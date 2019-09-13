from bs4 import BeautifulSoup
import requests
import numpy as np
import pandas as pd 
# https://github.com/block8437/gender.py
from gender import getGenders 
from datetime import datetime
import pathlib
import sys
import os
from argparse import ArgumentParser


ROOT_URL = "https://isa.epfl.ch/imoniteur_ISAP"

msc_bsc_dir = f"emails/{datetime.now().strftime('%Y_%m_%d')}/msc_bsc"
phd_dir = f"emails/{datetime.now().strftime('%Y_%m_%d')}/phd"



BSc_MSc_ACADEMIC_UNITS = {"All": "null",
                        "Architecture": "942293",
                        "Chimie et génie chimique": "246696",
                        "Cours de mathématiques spéciales": "943282",
                        "EME (EPFL Middle East)": "637841336",
                        "Génie civil": "942623",
                        "Génie mécanique": "944263",
                        "Génie électrique et électronique": "943936",
                        "Humanités digitales": "2054839157",
                        "Informatique": "249847",
                        "Ingénierie financière": "120623110",
                        "Management de la technologie": "946882",
                        "Mathématiques": "944590",
                        "Microtechnique": "945244",
                        "Physique": "945571",
                        "Science et génie des matériaux": "944917",
                        "Sciences et ingénierie de l'environnement": "942953",
                        "Sciences et technologies du vivant": "945901",
                        "Systèmes de communication": "946228"}
                        #"Section FCUE": "1574548993",



def myfun(x):
    if type(x.full_name) != np.float:
        if len(x.full_name.split()[-1]) != 1 and len(x.full_name.split()) < 4:
            return  x.full_name.split()[-1]
        else:
            first_name_part = x.email.split(".")[0]
            first_name, *rest = first_name_part.split("-")
            return first_name
                        

def collect_male_female_names():
    # getting all_male_names, and all_female_names
    skiprows=2
    list_df2 = pd.read_html(f"AllMScBSc.html", skiprows=skiprows, header=0) #, display_only=False)
    df2 = list_df2[0]
    df2.columns = ["gender", "full_name", "bsc", "msc", "spec", "filiere_opt",
                    "minor", "status", "exchange_type", "exchange_school", "sciper", "nationality"]

    with open(f"AllMScBSc.html", "r") as f:
        soup = BeautifulSoup(f, "html.parser")
        tb = soup.find_all('table')[0]

    data = [[td.a.get('href', None) if td.find('a') else ''.join(td.stripped_strings) for td in row.find_all('td')] for row in tb.find_all('tr')]
    df2["email"] = pd.DataFrame(data[skiprows+1:])[1]

    df2.email = df2.email.apply(lambda x: x[7:] if x and x.startswith("mailto:") else x)

    df2 = df2[df2["gender"].isin(["Mister", "Monsieur", "Miss", "Madam"])]
    df2["first_name"] = df2.apply(lambda row: myfun(row), axis=1)

    if os.path.isfile("male_names.txt"):
        with open("male_names.txt", "r") as f:
            old_male_names = set(f.read().splitlines())
    else:
        old_male_names = set()
    
    if os.path.isfile("female_names.txt"):
        with open("female_names.txt", "r") as f:
            old_female_names = set(f.read().splitlines())
    else:
        old_female_names = set()
        
    all_male = df2[df2.gender.isin(["Mister", "Monsieur"])]
    all_female = df2[df2.gender.isin(["Miss", "Madam"])]
    
    all_male_names = set(all_male.first_name.apply(str.lower)) | old_male_names
    all_female_names = set(all_female.first_name.apply(str.lower)) | old_female_names
    
    # remove empty str
    all_male_names = [i for i in all_male_names if i] 
    all_female_names = [i for i in all_female_names if i] 
    
    with open("male_names.txt", "w") as f:
        f.write("\n".join(all_male_names))
    
    with open("female_names.txt", "w") as f:
        f.write("\n".join(all_female_names))

    return all_male_names, all_female_names


def gender_estimator(df):
    all_male_names, all_female_names = collect_male_female_names()

    def estimate_gender(x):
        if x.first_name.lower() in all_male_names:
            return "Mister"
        elif x.first_name.lower() in all_female_names:
            return "Miss"
        else:
            return np.NaN

    df["gender"] = df.apply(lambda row: estimate_gender(row), axis=1)

    names_still_to_check = list(set(df[df.gender.isnull()].first_name.apply(str.lower)))
    names_still_to_check = [x.split("-")[0] for x in names_still_to_check]
    names_gender_website = []

    for x in np.arange(len(names_still_to_check), step=10):
        if x+10 <= len(names_still_to_check):
            names_gender_website.extend(getGenders(names_still_to_check[x:x+10]))
    names_gender_website.extend(getGenders(names_still_to_check[x:x+10]))

    website_estimation={}

    for real, estimated in zip(names_still_to_check, names_gender_website):
        website_estimation[real] = estimated[0]
    
    def estimate_gender_website(x):
        first_name = x.first_name.lower()
        if first_name in website_estimation.keys():
            if website_estimation[first_name] == 'female':
                return "Miss"
            elif website_estimation[first_name] == 'male':
                return "Mister"
            else:
                return np.NaN
        elif first_name in all_male_names:
            return "Mister"
        elif first_name in all_female_names:
            return "Miss"
        else:
            return np.NaN

    df["gender"] = df.apply(lambda row: estimate_gender_website(row), axis=1)

    return df["gender"]


def extract_phd_emails(ww_x_username, ww_x_password, PHD_public, PHD_report_type, PHD_ww_x_SECTION, PHD_ww_c_langue, PHD_ww_x_PDOC,
                       PHD_ww_x_DATE_EXM, PHD_ww_i_reportmodel, PHD_ww_i_reportModelXsl, PHD_zz_x_PDOC, PHD_zz_x_SECTION):
    """ Every field from the query:
        PHD_public = True
        PHD_report_type = "HTML"                # HTML or XLS = .XLS or .html
        PHD_ww_x_SECTION = ""                   # Form el.3: section CODE
        PHD_ww_c_langue = ""
        PHD_ww_x_PDOC = ""                      # Form el.1: Doctoral Program CODE
        PHD_ww_x_DATE_EXM = ""                  # Form el.2: And past student since (dd.mm.yyyy)
        PHD_ww_i_reportmodel = "46959103"       # Format: PhD 
        PHD_ww_i_reportModelXsl = "46959108"    # Format: PhD XSL
        PHD_zz_x_PDOC = ""                      # Form el.1: Doctoral Program NAME
        PHD_zz_x_SECTION = "Architecture"       # Form el.3: section NAME
    """
    PHD_url_template = f"{ROOT_URL}/!GED{'PUBLIC' if PHD_public else ''}REPORTS.{PHD_report_type}?"\
                                    f"ww_x_SECTION={PHD_ww_x_SECTION}&"\
                                    f"ww_c_langue={PHD_ww_c_langue}&"\
                                    f"dummy=ok&"\
                                    f"ww_x_PDOC={PHD_ww_x_PDOC}&"\
                                    f"ww_x_DATE_EXM={PHD_ww_x_DATE_EXM}&"\
                                    f"ww_i_reportmodel={PHD_ww_i_reportmodel}&"\
                                    f"ww_i_reportModelXsl={PHD_ww_i_reportModelXsl}&"\
                                    f"zz_x_PDOC={PHD_zz_x_PDOC}&"\
                                    f"zz_x_SECTION={PHD_zz_x_SECTION}"
    print(f"URL: {PHD_url_template}\n")

    with requests.Session() as s:
        s.post(f"{ROOT_URL}/!logins.tryToConnect", data= {'ww_x_username': ww_x_username, 'ww_x_password': ww_x_password})

        # An authorised request.
        r = s.get(PHD_url_template)

    list_df = pd.read_html(r.text, skiprows=1, header=0) 
    df = list_df[0]
    df.columns = ["full_name", "supervisor", "cursus", "section", "ratt", "email", "nationality", "sciper", "exmatriculation", "Unknown 9"]

    df["first_name"] = df.apply(lambda row: myfun(row),axis=1)
    df["gender"] = gender_estimator(df)

    df.sciper = df.sciper.astype(int)

    # save everybody
    pathlib.Path("DataAnalysis").mkdir(parents=True, exist_ok=True)
    writer_all = pd.ExcelWriter(f'DataAnalysis/All_PhD.xlsx')
    df.to_excel(writer_all, "PhD", index=False)
    writer_all.save()

    # save ladies' emails
    pathlib.Path(phd_dir).mkdir(parents=True, exist_ok=True)

    writer = pd.ExcelWriter(f'{phd_dir}/All_PhD.xlsx')

    df_ladies = df[df.gender.isin(["Miss", "Madame"])]

    for curs in df_ladies.cursus.value_counts().index:
        emails = list(set(df_ladies[df_ladies.cursus==curs].email))
        # discard nans
        emails = [email for email in emails if type(email)==str]
        number = len(emails)

        filename = f"{phd_dir}/{curs.replace(' ', '_')}_({number} emails).txt"
        print(f"Writing file {filename}...")

        
        with open(filename, "w") as f:
            f.write(";".join(emails))
            
        sheet_name = curs
        df_ladies[df_ladies.cursus==curs].to_excel(writer, sheet_name, index=False)

    writer.save()

    emails = list(set(df_ladies.email))
    # discard nans
    emails = [email for email in emails if type(email)==str]
    number = len(emails)

    filename = f"{phd_dir}/All_({number} emails).txt"
    with open(filename, "w") as f:
        f.write(";".join(emails))



def extract_msc_bsc_emails(ww_x_username, ww_x_password, MSC_BSC_public, MSC_BSC_report_type, MSC_BSC_ww_x_PERIODE_PEDAGO, MSC_BSC_ww_x_UNITE_ACAD,
                           MSC_BSC_ww_i_reportModel, MSC_BSC_ww_x_GPS, MSC_BSC_ww_x_PERIODE_ACAD, MSC_BSC_ww_i_reportModelXsl, MSC_BSC_ww_x_HIVERETE):
    """
        MSC_BSC_public = False                      # when public=False, then we can get the emails as well
        MSC_BSC_report_type = "HTML"                # HTML or XLS = .XLS or .html
        MSC_BSC_ww_x_PERIODE_PEDAGO = "null"        # Form el.3: Periode Pedagogique
        MSC_BSC_ww_x_UNITE_ACAD = "null"            # Form el.1: Unite Academique
        MSC_BSC_ww_i_reportModel = "133685247"      # Format: MSc/BSc (other option is code for PhD)
        MSC_BSC_ww_x_GPS = "-1"                     # Under filter, e.g. Architecture, 1985-1986, Semestre -1
        MSC_BSC_ww_x_PERIODE_ACAD = "1866893861" # 2018-2019   # Form el.2: Periode Academique
        MSC_BSC_ww_i_reportModelXsl = "133685270"   # Format: MSc/BSc XSL
        MSC_BSC_ww_x_HIVERETE = "null"              # Form el.4: Type de semestre  
    """
    pathlib.Path(msc_bsc_dir).mkdir(parents=True, exist_ok=True)

    # to save ladies
    writer = pd.ExcelWriter(f'{msc_bsc_dir}/All_BScMSc.xlsx')

    # to save everybody
    pathlib.Path("DataAnalysis").mkdir(parents=True, exist_ok=True)
    writer_all = pd.ExcelWriter('DataAnalysis/All_MSc_BSc.xlsx')

    for acad_unit_name, MSC_BSC_ww_x_UNITE_ACAD in BSc_MSc_ACADEMIC_UNITS.items():

        print(f"Collecting emails for academic unit {acad_unit_name.upper()}...")

        # https://isa.epfl.ch/imoniteur_ISAP/!GEDREPORTS.html?ww_x_PERIODE_PEDAGO=null&ww_x_UNITE_ACAD=null&ww_i_reportModel=133685247&ww_x_GPS=-1&ww_x_PERIODE_ACAD=1866893861&ww_i_reportModelXsl=133685270&ww_x_HIVERETE=null
        MSC_BSC_url_template = f"{ROOT_URL}/!GED{'PUBLIC' if MSC_BSC_public else ''}REPORTS.{MSC_BSC_report_type}?"\
                                        f"ww_x_PERIODE_PEDAGO={MSC_BSC_ww_x_PERIODE_PEDAGO}&"\
                                        f"ww_x_UNITE_ACAD={MSC_BSC_ww_x_UNITE_ACAD}&"\
                                        f"ww_i_reportModel={MSC_BSC_ww_i_reportModel}&"\
                                        f"ww_x_GPS={MSC_BSC_ww_x_GPS}&"\
                                        f"ww_x_PERIODE_ACAD={MSC_BSC_ww_x_PERIODE_ACAD}&"\
                                        f"ww_i_reportModelXsl={MSC_BSC_ww_i_reportModelXsl}&"\
                                        f"ww_x_HIVERETE={MSC_BSC_ww_x_HIVERETE}"
        print(f"URL: {MSC_BSC_url_template}\n")
        
        with requests.Session() as s:
            s.post(f"{ROOT_URL}/!logins.tryToConnect", data={'ww_x_username': ww_x_username, 'ww_x_password': ww_x_password})

            # An authorised request.
            r = s.get(MSC_BSC_url_template)

        soup = BeautifulSoup(r.text, "html.parser")

        # just save for PhD gender determination
        with open(f"AllMScBSc.html", "w") as f:
            f.write(str(soup))

        tb = soup.find_all('table')[0]

        list_df = pd.read_html(r.text, skiprows=1, header=0) 
        df = list_df[0]
        df.columns = ["gender", "name", "bsc", "msc", "spec", "filiere_opt", "minor", 
                    "status", "exchange_type", "exchange_school", "sciper", "nationality"]

        data = [[td.a.get('href', None) if td.find('a') else ''.join(td.stripped_strings) for td in row.find_all('td')] for row in tb.find_all('tr')]
        df["email"] = pd.DataFrame(data[2:])[1]
        df.email = df.email.apply(lambda x: x[7:] if x and x.startswith("mailto:") else x)

        df = df[df["gender"].isin(["Mister", "Monsieur", "Miss", "Madam"])]

        # unwanted = df.columns[df.columns.str.startswith('Unnamed')]
        # df.drop(unwanted, axis=1, inplace=True)

        df = df.groupby(['sciper', 'email']).agg({'spec': 'first', 
                                            'bsc': 'first', 
                                            'msc': 'first', 
                                            'filiere_opt':'first', 
                                            'minor': 'first',
                                            'status':'first',
                                            'exchange_type': 'first',
                                            'exchange_school': 'first',
                                            'name': 'first',
                                            'nationality': 'first',
                                            'gender': 'first'}).reset_index()
        df.sciper = df.sciper.astype(int)

        df["academic_unit"] = acad_unit_name

        df_ladies = df[df.gender.isin(["Miss", "Madame"])]

        # ladies emails
        emails = ';'.join([e for e in list(set(df_ladies.email))])
        number = len(set(df_ladies.email))
        
        df_ladies = df_ladies.drop_duplicates()

        # save to file
        filename = f"{msc_bsc_dir}/{acad_unit_name.replace(' ', '_')}_({number} emails).txt"
        
        print(f"Writing file {filename}...")
        with open(filename, "w+") as f:
            f.write(emails)

        # sheet name limit is 30 characters
        sheet_name = acad_unit_name[:30]
        df_ladies.to_excel(writer, sheet_name, index=False)

        # save everybody
        df.to_excel(writer_all, sheet_name, index=False)

    # save everybody
    writer_all.save()

    # save 
    writer.save()


if __name__ == "__main__":

    parser = ArgumentParser(description='EPFL student list scrapper')
    parser.add_argument('--username', required=True,
                        help='EPFL username')
    parser.add_argument('--password', required=True,
                        help='EPFL password')

    args = parser.parse_args()

    # academic_period = {"2018-2019": "1866893861"}

    ### MSc and BSc
    extract_msc_bsc_emails(args.username, args.password, MSC_BSC_public=False, MSC_BSC_report_type="HTML", MSC_BSC_ww_x_PERIODE_PEDAGO="null", 
                            MSC_BSC_ww_x_UNITE_ACAD=None, MSC_BSC_ww_i_reportModel="133685247", 
                            MSC_BSC_ww_x_GPS="-1", MSC_BSC_ww_x_PERIODE_ACAD="1866893861", 
                            MSC_BSC_ww_i_reportModelXsl="133685270", MSC_BSC_ww_x_HIVERETE="null")

    ### PhD
    extract_phd_emails(args.username, args.password, 
                        PHD_public=False, PHD_report_type="HTML", 
                        PHD_ww_x_SECTION="", PHD_ww_c_langue="", PHD_ww_x_PDOC="",
                        PHD_ww_x_DATE_EXM="", PHD_ww_i_reportmodel="46959103", 
                        PHD_ww_i_reportModelXsl="46959108", PHD_zz_x_PDOC="", 
                        PHD_zz_x_SECTION="")
