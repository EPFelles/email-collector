# EPFL Email Collector
Collect EPFL emails

# Collect
```
python run.py --username YOUR_EPFL_USERNAME --password YOUR_EPFL_PASSWORD
```

# Output
The emails will be located in directory `emails/`.
For MSc and BSc students, the directory is: `emails/DATE_LAST_COLLECTED/msc_bsc/*`
For PhD students, the directory is: `emails/DATE_LAST_COLLECTED/phd/*`

Data for data stats is collected in `DataAnalysis/All_MSc_BSc.xlsx` and `DataAnalysis/All_PhD.xlsx`. The report (currently for 2019) can be found in Analysis.ipynb notebook.
