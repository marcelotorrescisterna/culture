"""
Build txt files from pdf fiñes

@Marcelo Torres Cisterna
@Datellus

"""

import pandas as pd
import numpy as np
import re
from PyPDF2 import PdfReader
import os
from textcleaningutils import *
import shutil as sh

INPUT_FOLDER = "data/pdf_files"
OUTPUT_FOLDER = "data/input"
BAD_PDF_FOLDER = "data/bad_pdf_files"
docs = os.listdir(INPUT_FOLDER)
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

if not os.path.exists(OUTPUT_FOLDER + "/txtfiles/"):
    os.makedirs(OUTPUT_FOLDER + "/txtfiles/")
    
if not os.path.exists(BAD_PDF_FOLDER):
    os.makedirs(BAD_PDF_FOLDER)

if __name__ == "__main__":
    corpus = str()
    ids = str()
    id2doc = []
    totaldocs = len(docs)
    for m, doc in enumerate(docs):
        try:
            print(f"PROCESSING FILE : {doc} , File Number : {m+1} / {totaldocs}")
            ########## BASIC SETUP ###########
            reader = PdfReader(f"{INPUT_FOLDER}/{doc}")
            number_of_pages = len(reader.pages)
            doc_name = doc.replace("pdf" , "txt")
            tcfinder = False

            ########### OBS ON QUALITY ##########
            # Quality 1 : Best Earning Call Format
            # Quality 2 : Good Format, Missing Participants
            # Quality 3 : Good Format , Missing Participants and QA
            # Quality 4 : Good Format, Missing TC
            # Quality 5 : Plain Text

            ######## GETTING THE TABLE OF CONTENTS #######
            for i in range(number_of_pages):
                page = reader.pages[i]
                temp_text = page.extract_text()
                if "Table of Contents" in temp_text:
                    tcfinder = True
                    tcnumber = i
                    break
            table_contents = temp_text

            ######### ANALYZING THE STATUS OF THE TABLE OF CONTENTS ########
            table_contents = [1 if x in table_contents else 0 for x in ["Call Participants" , "Presentation" , "Question and Answer"]]
            if tcfinder and table_contents[0] == 1 and table_contents[1] == 1:
                participants_num = int(temp_text.split("\n")[-3].replace("." , "")[-1]) - 1
                presentation_num = int(temp_text.split("\n")[-2].replace("." , "")[-1]) - 1
                qa_num = int(temp_text.split("\n")[-1].replace("." , "").split(" ")[-1]) - 1
                quality = 1
            elif tcfinder and table_contents[0] == 0 and table_contents[2] == 1:
                participants_num = 0
                presentation_num = int(temp_text.split("\n")[-2].replace("." , "")[-1]) - 1
                qa_num = int(temp_text.split("\n")[-1].replace("." , "").split(" ")[-1]) - 1
                quality = 2
            elif tcfinder and table_contents[0] == 0 and table_contents[2] == 0:  
                participants_num = 0
                presentation_num = int(temp_text.split("\n")[-1].replace("." , "")[-1]) - 1
                qa_num = 0
                quality = 3

            ######### DEALING WITH MISSING TABLE OF CONTENTS ######    
            ##### In this case we have three options: A good structured Earning Call without TC , a Plain Text Or The REFINITIV Earning Call #####
            elif not tcfinder:
                ### We extract the content from the first page and if we find the Executives we have a plain text
                page = reader.pages[0]
                temp_text = page.extract_text()
                if "Executives"in temp_text:
                    table_contents = [2 , 2 , 2]
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
                ## 2024 EC VERSION            
                elif "CORPORATE PARTICIPANTS" in reader.pages[1].extract_text():
                    table_contents = [2 , 2 , 2]
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
                    table_contents = [3 , 3 , 3]

            ############################ PARTICIPANTS ################################

            #### If Quality is 1 or 4 which means there is a section with Call Participants, we go to that section
            if (quality in [1,4]):
                participants = str()
                for i in range(participants_num , presentation_num):
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
                        participants2.append(participants[i] + " " +participants[i+1])
                        skipper = True
                participants = participants2 
            #### If Quality is 2 this means we have a good structure but no participants, which means we need to extract them
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
                
            elif quality == 6 :
                mainpage = reader.pages[1]
                participants = mainpage.extract_text()
                participants = participants.split("PRESENTATION")[0].split("CORPORATE PARTICIPANTS")[1].strip().split("\n")
                participants = [x.strip() for x in participants]
                participants = [x for x in participants if x != "CONFERENCE CALL PARTICIPANTS"]
                participants = participants + ["[Operator Instructions]"] + ["Operator"] + ["(Operator Instructions)"] 


            #### PROCESSING THE WHOLE TEXT ####
            if (quality in [1 , 2 , 4]):
                page = reader.pages[qa_num]
                maintext = page.extract_text()
                maintext = maintext.replace('[Operator Instructions]' , "").strip()
                maintext = participantsRemover(maintext , participants)
                maintext = firstPageCleaner(maintext)
                maintext = '   '.join(maintext)

                for i in range(qa_num+1 , number_of_pages-1):
                    ### Load the Page
                    page = reader.pages[i]
                    #print(f"============== Processing Page : {i} =============")
                    currenttext = page.extract_text()
                    currenttext = currenttext.replace('[Operator Instructions]' , "").strip()
                    ## Extract All Rights Reserved
                    currenttext = currenttext.split("All Rights reserved.")[1]
                    currenttext = currenttext.split("\n")
                    currenttext = [x for x in currenttext if len(x) != 0]

                    #### Particular Case ###
                    if i == (number_of_pages-2):
                        last_strong = 0
                        for h,c in enumerate(currenttext):
                            if "<strong>" in c[:9]:
                                last_strong = h
                        if last_strong != 0:
                            currenttext = currenttext[:last_strong]

                    ## Remove Participants in case they are in the first line
                    for p in participants:
                        try:
                            pattern = re.search(p , currenttext[0]).group()
                            currenttext = currenttext[1:] 
                        except:
                            currenttext = currenttext
                    ### Remove Participants and Numbers
                    currenttext = participantsRemover(currenttext , participants)
                    try:
                        currenttext = numCleanerold(currenttext,i)
                    except:
                        currenttext = currenttext
                    #currenttext = participantsRemover(currenttext , participants)     
                    ## Join Current Text
                    currenttext = '   '.join(currenttext)    
                    ## Join Whole Text
                    if len(maintext) != 0:
                        maintext = maintext + "   " + currenttext
                    else:
                        maintext = maintext + currenttext
            elif quality == 5:
                page = reader.pages[qa_num]
                maintext = page.extract_text()
                maintext = maintext.replace('[Operator Instructions]' , "").strip()
                maintext = maintext.split("Question and Answer")[1]
                maintext = participantsRemover(maintext , participants)
                maintext = [x.strip() for x in maintext]
                maintext = '   '.join(maintext)    
                for i in range(qa_num + 1 , number_of_pages):
                    ### Load the Page
                    #print(f"========= PROCESSING PAGE {i} ==========")
                    page = reader.pages[i]
                    currenttext = page.extract_text().strip()
                    currenttext = currenttext.replace('[Operator Instructions]' , "").strip()
                    if "Disclaimer" not in currenttext:
                        ## Check if we are in the Disclaimer Section
                        currenttext = participantsRemover(currenttext , participants)
                        ## Join Current Text
                        currenttext = [x.strip() for x in currenttext]
                        currenttext = '   '.join(currenttext).strip()
                        #print(currenttext)
                        ## Join Whole Text
                        if len(maintext) != 0:
                            maintext = maintext + "   " + currenttext
                        else:
                            maintext = maintext + currenttext
                        #print("=========== MAINTEXT ========")
                        #print(maintext)
                    ## If we are in the Disclaimer Section
                    else:
                        currenttext = currenttext.split("Disclaimer")[0]
                        currenttext = participantsRemover(currenttext , participants)
                        currenttext = [x.strip() for x in currenttext]
                        currenttext = '   '.join(currenttext).strip()
                        #print(currenttext)
                        if len(maintext) != 0:
                            maintext = maintext + "   " + currenttext
                        else:
                            maintext = maintext + currenttext
                        break 
            elif quality == 6:
                page = reader.pages[0]
                currenttext = page.extract_text().strip()
                disclaimer = currenttext.split("affiliated companies")[0] + "affiliated companies."
                page = reader.pages[qa_num]
                maintext = page.extract_text()
                maintext = maintext.replace('(Operator Instructions)' , "").strip()
                maintext = maintext.split("QUESTIONS AND ANSWERS")[1]
                maintext = participantsRemover(maintext , participants)
                maintext = [x.strip() for x in maintext]
                maintext = '   '.join(maintext)
                for i in range(qa_num + 1 , number_of_pages):
                    ### Load the Page
                    # print(f"========= PROCESSING PAGE {i} ==========")
                    page = reader.pages[i]
                    currenttext = page.extract_text().strip()
                    currenttext = currenttext.replace('(Operator Instructions)' , "").strip()
                    currenttext = currenttext.split(f"{disclaimer}{i+1}")[1].strip()
                    
                    if "DISCLAIMER" not in currenttext:
                        ## Check if we are in the Disclaimer Section
                        currenttext = participantsRemover(currenttext , participants)
                        ## Join Current Text
                        currenttext = [x.strip() for x in currenttext]
                        currenttext = '   '.join(currenttext).strip()
                        #print(currenttext)
                        ## Join Whole Text
                        if len(maintext) != 0:
                            maintext = maintext + "   " + currenttext
                        else:
                            maintext = maintext + currenttext
                        #print("=========== MAINTEXT ========")
                        #print(maintext)
                    ## If we are in the Disclaimer Section
                    else:
                        currenttext = currenttext.split("DISCLAIMER")[0]
                        currenttext = participantsRemover(currenttext , participants)
                        currenttext = [x.strip() for x in currenttext]
                        currenttext = '   '.join(currenttext).strip()
                        #print(currenttext)
                        if len(maintext) != 0:
                            maintext = maintext + "   " + currenttext
                        else:
                            maintext = maintext + currenttext
                        break    
            ############# Save text #############
            idnum = f"{m}.F"
            with open(f'{OUTPUT_FOLDER}/txtfiles/{doc_name}', 'w') as f:
                f.write(maintext)
            corpus = corpus + maintext + "\r\n"
            ids = ids + idnum + "\r\n"
            d = {
                "idnum" : idnum ,
                "file" : f"{doc}"
            }
            id2doc.append(d)
        except Exception as e:
            print(e)
            print(f"ERROR PROCESSING FILE : {doc}")
            SOURCE = f"{INPUT_FOLDER}/{doc}"
            DEST = f"{BAD_PDF_FOLDER}/{doc}"
            sh.move(SOURCE, DEST)
            
    id2doc = pd.DataFrame(id2doc)    
    id2doc.to_excel(f"{OUTPUT_FOLDER}/id2doc.xlsx")
    with open(f'{OUTPUT_FOLDER}/documents.txt', 'w') as f:
        f.write(corpus)
    with open(f'{OUTPUT_FOLDER}/document_ids.txt', 'w') as f:
        f.write(ids)