import re
import pandas as pd
import numpy as np


def numCleanerold(text , page_num):
    test = text[:5]
    if len(str(page_num + 1)) < 2:
        for i,c in enumerate(test):
            #### PageNUM 1 digito
            try:
                pattern = re.search(f"[{page_num+1}]" + "{1,4}[a-zA-Z0-9]" , c).group()
                break
            except:
                pattern = re.search(f"[{page_num[0]}][{page_num[1]}]" + "\D" , c).group()
                break
        cleaned_text = [pattern[1] + test[i].split(pattern)[1]] + text[i+1:]
        #### PageNUM 2 digito
    else:
        page_num = page_num + 1
        page_num = str(page_num)
        for i,c in enumerate(test):
            try:
                pattern = re.search(f"[{page_num[0]}][{page_num[1]}]" + "{1,4}[a-zA-Z0-9]" , c).group()
                break
            except:
                pattern = re.search(f"[{page_num[0]}][{page_num[1]}]" + "\D" , c).group()
                break
        cleaned_text = [pattern[-1] + test[i].split(pattern)[1]] + text[i+1:] 
    return cleaned_text

def numCleaner(text , page_num):
    test = text[:5]
    if len(str(page_num + 1)) < 2:
        for i,c in enumerate(test):
            #### PageNUM 1 digito
            if i >= 2:
                try:
                    pattern = re.search(f"[{page_num+1}]" + "{1,4}[a-zA-Z0-9]" , c).group()
                    break
                except:
                    pattern = re.search(f"[{page_num+1}]" + "\D" , c).group()
                    break
        cleaned_text = [pattern[1] + test[i].split(pattern)[1]] + text[i+1:]
        #### PageNUM 2 digito
    else:
        page_num = page_num + 1
        page_num = str(page_num)
        for i,c in enumerate(test):
            if i >= 2:
                try:
                    pattern = re.search(f"[{page_num[0]}][{page_num[1]}]" + "{1,4}[a-zA-Z0-9]" , c).group()
                    break
                except:
                    pattern = re.search(f"[{page_num[0]}][{page_num[1]}]" + "\D" , c).group()
                    break
        cleaned_text = [pattern[-1] + test[i].split(pattern)[1]] + text[i+1:] 
    return cleaned_text



def participantsRemoverOld(text , participants):
    try:
        new_text = []
        text = text.split("\n")
        for x in text:
            if x not in participants:
                new_text.append(x)
    except:
        new_text = []
        for x in text:
            if x not in participants:
                new_text.append(x)        
    return new_text

def participantsRemover(text , participants):
    try:
        new_text = []
        text = text.split("\n")
        text = [x.strip() for x in text]
        for x in text:
            if x not in participants:
                new_text.append(x)
            else:
                x = "PAREND"
                new_text.append(x)
        new_text = " ".join(new_text)
        new_text = new_text.split("PAREND")
        
    except:
        new_text = []
        for x in text:
            if x not in participants:
                new_text.append(x) 
            else:
                x = "PAREND"
                new_text.append(x)
        new_text = " ".join(new_text)
        new_text = new_text.split("PAREND")
    new_text = [x.strip() for x in new_text]
    new_text = [x for x in new_text if len(x) != 0]
    return new_text

def firstPageCleaner(text):
    temp_text = text[:5]
    for i,c in enumerate(temp_text):
        if "Question and Answer" in c:
            break
    return text[i+1:]