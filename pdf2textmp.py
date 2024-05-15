import pandas as pd
import numpy as np
import re
import argparse
from PyPDF2 import PdfReader
import os
from textcleaningutils import *
import shutil as sh
from multiprocessing import Pool, Manager
import time

def process_document(index, total, doc, INPUT_FOLDER, OUTPUT_FOLDER, BAD_PDF_FOLDER, corpus_list, ids_list, id2doc_list):
    try:
        print(f"PROCESSING FILE : {doc} ({index + 1}/{total})")
        reader = PdfReader(f"{INPUT_FOLDER}/{doc}")
        number_of_pages = len(reader.pages)
        doc_name = doc.replace("pdf", "txt")
        tcfinder = False

        for i in range(number_of_pages):
            page = reader.pages[i]
            temp_text = page.extract_text()
            if "Table of Contents" in temp_text:
                tcfinder = True
                tcnumber = i
                break
        table_contents = temp_text

        table_contents = [1 if x in table_contents else 0 for x in ["Call Participants", "Presentation", "Question and Answer"]]
        if tcfinder and table_contents[0] == 1 and table_contents[1] == 1:
            participants_num = int(temp_text.split("\n")[-3].replace(".", "")[-1]) - 1
            presentation_num = int(temp_text.split("\n")[-2].replace(".", "")[-1]) - 1
            qa_num = int(temp_text.split("\n")[-1].replace(".", "").split(" ")[-1]) - 1
            quality = 1
        elif tcfinder and table_contents[0] == 0 and table_contents[2] == 1:
            participants_num = 0
            presentation_num = int(temp_text.split("\n")[-2].replace(".", "")[-1]) - 1
            qa_num = int(temp_text.split("\n")[-1].replace(".", "").split(" ")[-1]) - 1
            quality = 2
        elif tcfinder and table_contents[0] == 0 and table_contents[2] == 0:
            participants_num = 0
            presentation_num = int(temp_text.split("\n")[-1].replace(".", "")[-1]) - 1
            qa_num = 0
            quality = 3
        elif not tcfinder:
            page = reader.pages[0]
            temp_text = page.extract_text()
            if "Executives" in temp_text:
                table_contents = [2, 2, 2]
                quality = 5
                for i in range(number_of_pages):
                    page = reader.pages[i]
                    temp_text = page.extract_text()
                    if "Call Participants" in temp_text:
                        participants_num = i
                        break
                    else:
                        participants_num = 99
                for i in range(number_of_pages):
                    page = reader.pages[i]
                    temp_text = page.extract_text()
                    if "Presentation" in temp_text:
                        presentation_num = i
                        break
                    else:
                        presentation_num = 99
                for i in range(number_of_pages):
                    page = reader.pages[i]
                    temp_text = page.extract_text()
                    if "Question and Answer" in temp_text:
                        qa_num = i
                        break
                    else:
                        qa_num = 99
            elif "CORPORATE PARTICIPANTS" in reader.pages[1].extract_text():
                table_contents = [2, 2, 2]
                quality = 6
                for i in range(number_of_pages):
                    page = reader.pages[i]
                    temp_text = page.extract_text()
                    if "Call Participants" in temp_text:
                        participants_num = i
                        break
                    else:
                        participants_num = 99
                for i in range(number_of_pages):
                    page = reader.pages[i]
                    temp_text = page.extract_text()
                    if "PRESENTATION" in temp_text:
                        presentation_num = i
                        break
                    else:
                        presentation_num = 99
                for i in range(number_of_pages):
                    page = reader.pages[i]
                    temp_text = page.extract_text()
                    if "QUESTIONS AND ANSWERS" in temp_text:
                        qa_num = i
                        break
                    else:
                        qa_num = 99
            else:
                for i in range(number_of_pages):
                    page = reader.pages[i]
                    temp_text = page.extract_text()
                    if "Call Participants" in temp_text:
                        participants_num = i
                        break
                    else:
                        participants_num = 99
                for i in range(number_of_pages):
                    page = reader.pages[i]
                    temp_text = page.extract_text()
                    if "Presentation" in temp_text:
                        presentation_num = i
                        break
                    else:
                        presentation_num = 99
                for i in range(number_of_pages):
                    page = reader.pages[i]
                    temp_text = page.extract_text()
                    if "Question and Answer" in temp_text:
                        qa_num = i
                        break
                    else:
                        qa_num = 99
                quality = 4
                table_contents = [3, 3, 3]

        if quality in [1, 4]:
            participants = str()
            for i in range(participants_num, presentation_num):
                page = reader.pages[participants_num]
                temp_text = page.extract_text()
                participants = participants + temp_text
            participants = participants.split("\n")
            participants = participants + ["Operator"]
            participants2 = []
            skipper = False
            for i in range(len(participants)):
                if participants[i][-1] != ",":
                    if not skipper:
                        participants2.append(participants[i])
                    skipper = False
                else:
                    participants2.append(participants[i] + " " + participants[i + 1])
                    skipper = True
            participants = participants2
        elif quality == 2:
            participants = []
            for i in range(number_of_pages):
                page = reader.pages[i]
                temp_text = page.extract_text()
                temp_text = temp_text.split("\n")
                for p in temp_text:
                    if ("<strong>" in p[:8]) and (p not in participants):
                        participants.append(p)
            participants = participants + ["Unknown Speaker"] + ["Operator"] + ["Unknown Operator"]
        elif quality == 5:
            mainpage = reader.pages[0]
            participants = mainpage.extract_text()
            participants = participants.split("Presentation")[0].split("Executives")[1].strip().split("\n")
            participants = [x.split("-")[0].strip() for x in participants]
            participants = [x for x in participants if x != "Analysts"]
            participants = participants + ["[Operator Instructions]"] + ["Operator"]
        elif quality == 6:
            mainpage = reader.pages[1]
            participants = mainpage.extract_text()
            participants = participants.split("PRESENTATION")[0].split("CORPORATE PARTICIPANTS")[1].strip().split("\n")
            participants = [x.strip() for x in participants]
            participants = [x for x in participants if x != "CONFERENCE CALL PARTICIPANTS"]
            participants = participants + ["[Operator Instructions]"] + ["Operator"] + ["(Operator Instructions)"]

        if quality in [1, 2, 4]:
            page = reader.pages[qa_num]
            maintext = page.extract_text()
            maintext = maintext.replace('[Operator Instructions]', "").strip()
            maintext = participantsRemover(maintext, participants)
            maintext = firstPageCleaner(maintext)
            maintext = '   '.join(maintext)
            for i in range(qa_num + 1, number_of_pages - 1):
                page = reader.pages[i]
                currenttext = page.extract_text()
                currenttext = currenttext.replace('[Operator Instructions]', "").strip()
                currenttext = currenttext.split("All Rights reserved.")[1]
                currenttext = currenttext.split("\n")
                currenttext = [x for x in currenttext if len(x) != 0]
                if i == (number_of_pages - 2):
                    last_strong = 0
                    for h, c in enumerate(currenttext):
                        if "<strong>" in c[:9]:
                            last_strong = h
                    if last_strong != 0:
                        currenttext = currenttext[:last_strong]
                for p in participants:
                    try:
                        pattern = re.search(p, currenttext[0]).group()
                        currenttext = currenttext[1:]
                    except:
                        currenttext = currenttext
                currenttext = participantsRemover(currenttext, participants)
                try:
                    currenttext = numCleanerold(currenttext, i)
                except:
                    currenttext = currenttext
                currenttext = '   '.join(currenttext)
                if len(maintext) != 0:
                    maintext = maintext + "   " + currenttext
                else:
                    maintext = maintext + currenttext
        elif quality == 5:
            page = reader.pages[qa_num]
            maintext = page.extract_text()
            maintext = maintext.replace('[Operator Instructions]', "").strip()
            maintext = participantsRemover(maintext, participants)
            maintext = firstPageCleaner(maintext)
            maintext = '   '.join(maintext)
            for i in range(qa_num + 1, number_of_pages - 1):
                page = reader.pages[i]
                currenttext = page.extract_text()
                currenttext = currenttext.replace('[Operator Instructions]', "").strip()
                currenttext = currenttext.split("All Rights reserved.")[1]
                currenttext = currenttext.split("\n")
                currenttext = [x for x in currenttext if len(x) != 0]
                if i == (number_of_pages - 2):
                    last_strong = 0
                    for h, c in enumerate(currenttext):
                        if "<strong>" in c[:9]:
                            last_strong = h
                    if last_strong != 0:
                        currenttext = currenttext[:last_strong]
                for p in participants:
                    try:
                        pattern = re.search(p, currenttext[0]).group()
                        currenttext = currenttext[1:]
                    except:
                        currenttext = currenttext
                currenttext = participantsRemover(currenttext, participants)
                try:
                    currenttext = numCleanerold(currenttext, i)
                except:
                    currenttext = currenttext
                currenttext = '   '.join(currenttext)
                if len(maintext) != 0:
                    maintext = maintext + "   " + currenttext
                else:
                    maintext = maintext + currenttext
        elif quality == 6:
            page = reader.pages[qa_num]
            maintext = page.extract_text()
            maintext = maintext.replace('[Operator Instructions]', "").strip()
            maintext = participantsRemover(maintext, participants)
            maintext = firstPageCleaner(maintext)
            maintext = '   '.join(maintext)
            for i in range(qa_num + 1, number_of_pages - 1):
                page = reader.pages[i]
                currenttext = page.extract_text()
                currenttext = currenttext.replace('[Operator Instructions]', "").strip()
                currenttext = currenttext.split("All Rights reserved.")[1]
                currenttext = currenttext.split("\n")
                currenttext = [x for x in currenttext if len(x) != 0]
                if i == (number_of_pages - 2):
                    last_strong = 0
                    for h, c in enumerate(currenttext):
                        if "<strong>" in c[:9]:
                            last_strong = h
                    if last_strong != 0:
                        currenttext = currenttext[:last_strong]
                for p in participants:
                    try:
                        pattern = re.search(p, currenttext[0]).group()
                        currenttext = currenttext[1:]
                    except:
                        currenttext = currenttext
                currenttext = participantsRemover(currenttext, participants)
                try:
                    currenttext = numCleanerold(currenttext, i)
                except:
                    currenttext = currenttext
                currenttext = '   '.join(currenttext)
                if len(maintext) != 0:
                    maintext = maintext + "   " + currenttext
                else:
                    maintext = maintext + currenttext

        with open(f"{OUTPUT_FOLDER}/txtfiles/{doc_name}", "w") as f:
            f.write(maintext)
        corpus_list.append(maintext)
        ids_list.append(doc)
        id2doc_list.append((doc, quality))

    except Exception as e:
        print(f"Error processing {doc}: {e}")
        sh.move(f"{INPUT_FOLDER}/{doc}", BAD_PDF_FOLDER)

def main():
    parser = argparse.ArgumentParser(description="PDF 2 Text")
    parser.add_argument("INPUT_FOLDER_ARG", help="path to input pdf")
    args = parser.parse_args()
    INPUT_FOLDER = args.INPUT_FOLDER_ARG
    OUTPUT_FOLDER = "data/input"
    BAD_PDF_FOLDER = "data/bad_pdf_files"
    docs = os.listdir(INPUT_FOLDER)
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
    if not os.path.exists(OUTPUT_FOLDER + "/txtfiles/"):
        os.makedirs(OUTPUT_FOLDER + "/txtfiles/")
    if not os.path.exists(BAD_PDF_FOLDER):
        os.makedirs(BAD_PDF_FOLDER)

    start_time = time.time()  # Record start time

    with Manager() as manager:
        corpus_list = manager.list()
        ids_list = manager.list()
        id2doc_list = manager.list()
        num_cores = 4  # specify the number of cores you want to use
        pool = Pool(processes=num_cores)
        results = [
            pool.apply_async(process_document, args=(index, len(docs), doc, INPUT_FOLDER, OUTPUT_FOLDER, BAD_PDF_FOLDER, corpus_list, ids_list, id2doc_list))
            for index, doc in enumerate(docs)
        ]
        for r in results:
            r.wait()
        pool.close()
        pool.join()

        corpus = ''.join(corpus_list)
        ids = ''.join(ids_list)
        id2doc = pd.DataFrame(list(id2doc_list))
        id2doc.to_excel(f"{OUTPUT_FOLDER}/id2doc.xlsx")
        with open(f'{OUTPUT_FOLDER}/documents.txt', 'w') as f:
            f.write(corpus)
        with open(f'{OUTPUT_FOLDER}/document_ids.txt', 'w') as f:
            f.write(ids)

    end_time = time.time()  # Record end time
    elapsed_time = end_time - start_time
    print(f"Total execution time: {elapsed_time:.2f} seconds")

if __name__ == "__main__":
    main()
