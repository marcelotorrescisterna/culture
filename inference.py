"""
The Custom Script is used to preprocess the texts to Run the Measuring Corporate Culture Model and Score Documents

@Marcelo Torres Cisterna
@Datellus

"""
import datetime
import itertools
import os
from pathlib import Path
import tqdm as tqdm
import functools
import logging
import sys
from culture import culture_models, file_util, preprocess , culture_dictionary , file_util 
import pickle
from collections import defaultdict
from operator import itemgetter
import pandas as pd
from tqdm import tqdm as tqdm
from stanza.server import CoreNLPClient
import global_options
from collections import Counter, OrderedDict, defaultdict
import math
import numpy as nps

def process_line(line, lineID):
    """Process each line and return a tuple of sentences, sentence_IDs, 
    
    Arguments:
        line {str} -- a document 
        lineID {str} -- the document ID
    
    Returns:
        str, str -- processed document with each sentence in a line, 
                    sentence IDs with each in its own line: lineID_0 lineID_1 ...
    """
    try:
        sentences_processed, doc_sent_ids = corpus_preprocessor.process_document(
            line, lineID
        )
    except Exception as e:
        print(e)
        print("Exception in line: {}".format(lineID))
    return "\n".join(sentences_processed), "\n".join(doc_sent_ids)


def process_largefile(
    input_file,
    output_file,
    input_file_ids,
    output_index_file,
    function_name,
    chunk_size=100,
    start_index=None,
):
    """ A helper function that transforms an input file + a list of IDs of each line (documents + document_IDs) to two output files (processed documents + processed document IDs) by calling function_name on chunks of the input files. Each document can be decomposed into multiple processed documents (e.g. sentences). 
    Supports parallel with Pool.

    Arguments:
        input_file {str or Path} -- path to a text file, each line is a document
        ouput_file {str or Path} -- processed linesentence file (remove if exists)
        input_file_ids {str]} -- a list of input line ids
        output_index_file {str or Path} -- path to the index file of the output
        function_name {callable} -- A function that processes a list of strings, list of ids and return a list of processed strings and ids.
        chunk_size {int} -- number of lines to process each time, increasing the default may increase performance
        start_index {int} -- line number to start from (index starts with 0)

    Writes:
        Write the ouput_file and output_index_file
    """
    try:
        if start_index is None:
            # if start from the first line, remove existing output file
            # else append to existing output file
            os.remove(str(output_file))
            os.remove(str(output_index_file))
    except OSError:
        pass
    assert file_util.line_counter(input_file) == len(
        input_file_ids
    ), "Make sure the input file has the same number of rows as the input ID file. "

    with open(input_file, newline="\n", encoding="utf-8", errors="ignore") as f_in:
        line_i = 0
        # jump to index
        if start_index is not None:
            # start at start_index line
            for _ in (range(start_index)):
                next(f_in)
            input_file_ids = input_file_ids[start_index:]
            line_i = start_index
        for next_n_lines, next_n_line_ids in zip(
            itertools.zip_longest(*[f_in] * chunk_size),
            itertools.zip_longest(*[iter(input_file_ids)] * chunk_size),
        ):
            line_i += chunk_size
            print(datetime.datetime.now())
            print(f"Processing line: {line_i}.")
            next_n_lines = list(filter(None.__ne__, next_n_lines))
            next_n_line_ids = list(filter(None.__ne__, next_n_line_ids))
            output_lines = []
            output_line_ids = []
            # Use parse_parallel.py to speed things up
            for output_line, output_line_id in map(
                function_name, next_n_lines, next_n_line_ids
            ):
                output_lines.append(output_line)
                output_line_ids.append(output_line_id)
            output_lines = "\n".join(output_lines) + "\n"
            output_line_ids = "\n".join(output_line_ids) + "\n"
            with open(output_file, "a", newline="\n") as f_out:
                f_out.write(output_lines)
            if output_index_file is not None:
                with open(output_index_file, "a", newline="\n") as f_out:
                    f_out.write(output_line_ids)

def clean_file(in_file, out_file):
    """clean the entire corpus (output from CoreNLP)
    
    Arguments:
        in_file {str or Path} -- input corpus, each line is a sentence
        out_file {str or Path} -- output corpus
    """
    a_text_clearner = preprocess.text_cleaner()
    process_largefile(
        input_file=in_file,
        output_file=out_file,
        input_file_ids=[
            str(i) for i in range(file_util.line_counter(in_file))
        ],  # fake IDs (do not need IDs for this function).
        output_index_file=None,
        function_name=functools.partial(a_text_clearner.clean),
        chunk_size=200000,
    )

def construct_doc_level_corpus(sent_corpus_file, sent_id_file):
    """Construct document level corpus from sentence level corpus and write to disk.
    Dump "corpus_doc_level.pickle" and "doc_ids.pickle" to Path(global_options.OUTPUT_FOLDER, "scores", "temp"). 
    
    Arguments:
        sent_corpus_file {str or Path} -- The sentence corpus after parsing and cleaning, each line is a sentence
        sent_id_file {str or Path} -- The sentence ID file, each line correspond to a line in the sent_co(docID_sentenceID)
    
    Returns:
        [str], [str], int -- a tuple of a list of documents, a list of document IDs, and the number of documents
    """
    print("Constructing doc level corpus")
    # sentence level corpus
    sent_corpus = file_util.file_to_list(sent_corpus_file)
    sent_IDs = file_util.file_to_list(sent_id_file)
    assert len(sent_IDs) == len(sent_corpus)
    # doc id for each sentence
    doc_ids = [x.split("_")[0] for x in sent_IDs]
    # concat all text from the same doc
    id_doc_dict = defaultdict(lambda: "")
    for i, id in enumerate(doc_ids):
        id_doc_dict[id] += " " + sent_corpus[i]
    # create doc level corpus
    corpus = list(id_doc_dict.values())
    doc_ids = list(id_doc_dict.keys())
    assert len(corpus) == len(doc_ids)
    with open(
        Path(global_options.OUTPUT_FOLDER, "scores", "temp", "corpus_doc_level.pickle"),
        "wb",
    ) as out_f:
        pickle.dump(corpus, out_f)
    with open(
        Path(global_options.OUTPUT_FOLDER, "scores", "temp", "doc_ids.pickle"), "wb"
    ) as out_f:
        pickle.dump(doc_ids, out_f)
    N_doc = len(corpus)
    return corpus, doc_ids, N_doc


def calculate_df(corpus):
    """Calcualte and dump a document-freq dict for all the words.
    
    Arguments:
        corpus {[str]} -- a list of documents
    
    Returns:
        {dict[str: int]} -- document freq for each word
    """
    print("Calculating document frequencies.")
    # document frequency
    df_dict = defaultdict(int)
    for doc in tqdm(corpus):
        doc_splited = doc.split()
        words_in_doc = set(doc_splited)
        for word in words_in_doc:
            df_dict[word] += 1
    # save df dict
    with open(
        Path(global_options.OUTPUT_FOLDER, "scores", "temp", "doc_freq.pickle"), "wb"
    ) as f:
        pickle.dump(df_dict, f)
    return df_dict


def load_doc_level_corpus():
    """load the corpus constructed by construct_doc_level_corpus()
    
    Returns:
        [str], [str], int -- a tuple of a list of documents, a list of document IDs, and the number of documents
    """
    print("Loading document level corpus.")
    with open(
        Path(global_options.OUTPUT_FOLDER, "scores", "temp", "corpus_doc_level.pickle"),
        "rb",
    ) as in_f:
        corpus = pickle.load(in_f)
    with open(
        Path(global_options.OUTPUT_FOLDER, "scores", "temp", "doc_ids.pickle"), "rb"
    ) as in_f:
        doc_ids = pickle.load(in_f)
    assert len(corpus) == len(doc_ids)
    N_doc = len(corpus)
    return corpus, doc_ids, N_doc


def score_tf(documents, doc_ids, expanded_dict):
    """
    Score documents using term freq. 
    """
    print("Scoring using Term-freq (tf).")
    score = culture_dictionary.score_tf(
        documents=documents,
        document_ids=doc_ids,
        expanded_words=expanded_dict,
        n_core=global_options.N_CORES,
    )
    score.to_csv(
        Path(global_options.OUTPUT_FOLDER, "scores", "scores_TF.csv"), index=False
    )


def score_tf_idf(documents, doc_ids, N_doc, method, expanded_dict, **kwargs):
    """Score documents using tf-idf and its variations
    
    Arguments:
        documents {[str]} -- list of documents
        doc_ids {[str]} -- list of document IDs
        N_doc {int} -- number of documents
        method {str} -- 
            TFIDF: conventional tf-idf 
            WFIDF: use wf-idf log(1+count) instead of tf in the numerator
            TFIDF/WFIDF+SIMWEIGHT: using additional word weights given by the word_weights dict
        expanded_dict {dict[str, set(str)]} -- expanded dictionary
    """
    if method == "TF":
        print("Scoring TF.")
        score_tf(documents, doc_ids, expanded_dict)
    else:
        print("Scoring TF-IDF.")
        # load document freq
        df_dict = pd.read_pickle(
            Path(global_options.OUTPUT_FOLDER, "scores", "temp", "doc_freq.pickle")
        )
        # score tf-idf
        score, contribution = culture_dictionary.score_tf_idf_custom(
            documents=documents,
            document_ids=doc_ids,
            expanded_words=expanded_dict,
            df_dict=df_dict,
            N_doc=N_doc,
            method=method,
            **kwargs
        )
        # save the document level scores (without dividing by doc length)
        score.to_csv(
            str(
                Path(
                    global_options.OUTPUT_FOLDER,
                    "scores",
                    "scores_{}.csv".format(method),
                )
            ),
            index=False,
        )
        # save word contributions
        pd.DataFrame.from_dict(contribution, orient="index").to_csv(
            Path(
                global_options.OUTPUT_FOLDER,
                "scores",
                "word_contributions",
                "word_contribution_{}.csv".format(method),
            )
        )

if __name__ == "__main__":
    print("============= Beginning Step 1 : Parsing File ==================")
    with CoreNLPClient(
            properties={
                "ner.applyFineGrained": "false",
                "annotators": "tokenize, ssplit, pos, lemma, ner, depparse",
            },
            memory=global_options.RAM_CORENLP,
            threads=global_options.N_CORES,
            timeout=12000000,
            max_char_length=1000000,
        ) as client:
            corpus_preprocessor = preprocess.preprocessor(client)
            in_file = Path(global_options.DATA_FOLDER, "input", "documents.txt")
            in_file_index = file_util.file_to_list(
                Path(global_options.DATA_FOLDER, "input", "document_ids.txt")
            )
            out_file = Path(
                global_options.DATA_FOLDER, "processed", "parsed", "documents.txt"
            )
            output_index_file = Path(
                global_options.DATA_FOLDER, "processed", "parsed", "document_sent_ids.txt"
            )
            process_largefile(
                input_file=in_file,
                output_file=out_file,
                input_file_ids=in_file_index,
                output_index_file=output_index_file,
                function_name=process_line,
                chunk_size=global_options.PARSE_CHUNK_SIZE,
            )
    print("============= Step 1 : Completed ==================")
    print("============= Beginning Step 2 : Creating Unigrams ==================")
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    ### UNIGRAMER ###
    # clean the parsed text (remove POS tags, stopwords, etc.) and create unigram---------------
    clean_file(
        in_file=out_file,
        out_file=Path(global_options.DATA_FOLDER, "processed", "unigram", "documents.txt"),
    )
    print("============= Step 2 : Completed ==================")
    print("============= Beginning Step 3 : Creating Bigrams ==================")
    ### BIGRAMER ###

    culture_models.file_bigramer(
        input_path= Path(global_options.DATA_FOLDER, "processed", "unigram", "documents.txt"),
        output_path=Path(global_options.DATA_FOLDER, "processed", "bigram", "documents.txt"),
        model_path=Path(global_options.MODEL_FOLDER, "phrases", "bigram.mod"),
        scoring="original_scorer",
        threshold=global_options.PHRASE_THRESHOLD,
    )
    print("============= Step 3 : Completed ==================")
    print("============= Beginning Step 4 : Creating Trigrams ==================")
    ### TRIGRAMER ###

    culture_models.file_bigramer(
        input_path=Path(global_options.DATA_FOLDER, "processed", "bigram", "documents.txt"),
        output_path=Path(global_options.DATA_FOLDER, "processed", "trigram", "documents.txt"),
        model_path=Path(global_options.MODEL_FOLDER, "phrases", "trigram.mod"),
        scoring="original_scorer",
        threshold=global_options.PHRASE_THRESHOLD,
    )
    print("============= Step 4 : Completed ==================")
    print("=================== Beginning Scoring Documents ======================")
    current_dict_path = "outputs/dict/expanded_dict.csv"
    culture_dict, all_dict_words = culture_dictionary.read_dict_from_csv(current_dict_path)
    word_sim_weights = culture_dictionary.compute_word_sim_weights(current_dict_path)

    sent_corpus_file = "data/processed/trigram/documents.txt"
    sent_id_file = "data/processed/parsed/document_sent_ids.txt"
    sent_corpus_file_orig = "data/processed/trained_params/trigram/documents.txt"
    sent_id_file_orig = "data/processed/trained_params/parsed/document_sent_ids.txt"
    sent_corpus = file_util.file_to_list(sent_corpus_file)
    sent_corpus_orig = file_util.file_to_list(sent_corpus_file_orig)

    corpus, doc_ids, N_doc = construct_doc_level_corpus(sent_corpus_file,sent_id_file)
    corpus_orig, doc_ids_orig, N_doc_orig = construct_doc_level_corpus(sent_corpus_file_orig,sent_id_file_orig)

    word_doc_freq = calculate_df(corpus_orig)

    methods = ["TF", "TFIDF", "WFIDF"]
    for method in methods:
        score_tf_idf(
            corpus,
            doc_ids,
            N_doc_orig,
            method=method,
            expanded_dict=culture_dict,
            normalize=False,
            word_weights=word_sim_weights,
        )