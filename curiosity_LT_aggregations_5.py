# -*- coding: utf-8 -*-

# 1. read all sheets, all new label columns -> validate subjects
# 3. read all sheets, all test columns -> validate trials/subjects
# 4. collect valid trial numerical data to dictionary (read_excel collects to ordered dictionary subj:df
# 4. collect valid trial quantitaive data to 2 dataframes: one for each test round
# 4. "First gaze after label" is qualitative -> one hot encoding
# 5. aggregate data
# 6. write data to file


# Fixation classification:
# 1. interpolation; < 100ms; monotonous; valid data for at least 2 samples at each end.
# 2. calculate velocity
# 3. classify fixation events based on velocity (all data)


import datetime
import os
import pandas as pd
import numpy as np
import constants_times_5 as c

given_date = "2020-02-03"
#logfiles = os.path.join(c.DIR, "data_to_read")
excel_file = f"curiosity_looking_data_{given_date}.xlsx"
input_excel = os.path.join(c.DIR, "tables", f"{given_date}", excel_file)
date = str(datetime.datetime.today().date())
dir_name = os.path.join(c.DIR, "tables", date)
try: os.mkdir(dir_name)
except FileExistsError: pass
output_excel = os.path.join(dir_name, "curiosity_LT_aggregated_{0}.xlsx".format(date))
#writer = pd.ExcelWriter(output_excel)


def main():

    valid_subjects = validate_subject_data()

    ord_dict = _read_input_data(sheet_name=valid_subjects)

#    for s in invalid_subjects:
#        del ord_dict[s]

    print("valid subject keys in dictionary: ", ord_dict.keys())

    df_int = pd.DataFrame(columns=c.quant_columns, index=ord_dict.keys())
    df_int.index.name = "subject"
    df_bor = pd.DataFrame(columns=c.quant_columns, index=ord_dict.keys())
    df_bor.index.name = "subject"

    for key, value in ord_dict.items():

        df = value

        for col in c.quant_columns:

            df_int.loc[key,col] = df.loc[0,col]
            df_bor.loc[key,col] = df.loc[1,col]

    df_latency = pd.concat([df_int, df_bor], ignore_index=True)

    mean_first_latency = get_mean_latency(df_latency)
    print("mean latency at first gaze after ATT look:", mean_first_latency)

    df_int = df_int.assign(First_gaze_on_interesting=df_int.apply(_fgaze_validate_onehot, target=1, axis=1))
    df_int = df_int.assign(First_gaze_on_other=df_int.apply(_fgaze_validate_onehot, target=2, axis=1))
    df_bor = df_bor.assign(First_gaze_on_interesting=df_bor.apply(_fgaze_validate_onehot, target=1, axis=1))
    df_bor = df_bor.assign(First_gaze_on_other=df_bor.apply(_fgaze_validate_onehot, target=2, axis=1))

    df_int = df_int.assign(Second_gaze_on_interesting=df_int.apply(_secgaze_validate_onehot, target=1, axis=1))
    df_int = df_int.assign(Second_gaze_on_other=df_int.apply(_secgaze_validate_onehot, target=2, axis=1))
    df_bor = df_bor.assign(Second_gaze_on_interesting=df_bor.apply(_secgaze_validate_onehot, target=1, axis=1))
    df_bor = df_bor.assign(Second_gaze_on_other=df_bor.apply(_secgaze_validate_onehot, target=2, axis=1))

    # set types in case of mismatch
    type_d = {col:"float" for col in c.aggr_columns}
    df_int = df_int.astype(type_d)
    df_bor = df_bor.astype(type_d)

    df_aggregated = pd.DataFrame(data=[df_int.mean(axis=0, numeric_only=None), df_bor.mean(axis=0, numeric_only=None)],
                                       columns=c.aggr_columns, index=["interesting", "other"])
    df_aggregated = df_aggregated.astype("float")

    print("df_aggregated head:", df_aggregated.head())

    df_aggregated.index.name = "label"

    try:
        os.mkdir(dir_name)
    except FileExistsError:
        pass

    df_int.to_excel(os.path.join(dir_name, "Familiar_label_trial_results_{0}.xlsx".format(date)))
    df_bor.to_excel(os.path.join(dir_name, "Novel_label_trial_results_{0}.xlsx".format(date)))
    df_aggregated.to_excel(output_excel, index=True)
    print("Aggregated data saved to excel.")


def _read_input_data(columns=c.columns, sheet_name=None, skiprows=15, nrows=3):

    print("reading excel file {0}.".format(excel_file))

    # ordered dictionary with sheet names as keys, dataframes as values
    ord_dict = pd.read_excel(input_excel, sheet_name=sheet_name, skiprows=skiprows, header=0, usecols=columns, nrows=nrows)

    return ord_dict


def validate_subject_data():
    """
    first validate familiarisation: min average 60% of look on screen
    second validate baseline and test phases: min average 60% of look on screen
    """
    teach_dict = _read_input_data(columns=c.teach_validation_columns, skiprows=7, nrows=4)
    test_dict = _read_input_data(columns=c.test_validation_columns, skiprows=15, nrows=2)

    invalid_subjects = []
    subjects = teach_dict.keys()

    for s in subjects:
        df = teach_dict[s]
        for col in c.teach_validation_columns:
            if df[col].mean() < 0.6:
                invalid_subjects.append(s)
                break

    quant_test_cols = c.test_validation_columns[:2]
    ag_col = c.test_validation_columns[2]

    for s in subjects:
        df = test_dict[s]
        for col in quant_test_cols:
            if s not in invalid_subjects:
                if df[col].mean() < 0.6:
                    invalid_subjects.append(s)

        if s not in invalid_subjects:
            for i in df.index:
                if df.at[i, ag_col] == "No":
                    invalid_subjects.append(s)
                    break

    print("invalid_subjects:",invalid_subjects)
    valid_subjects = [s for s in subjects if s not in invalid_subjects]
    return valid_subjects


def _fgaze_validate_onehot(row, target=None):
    """
    first_gaze mean will be:
        nr of trials where first_gaze on target / all_other trial
        all_other trial: on boring or on familiar or on int but latency too high
    """
    target_to_aoi = {1:"INT", 2:"BOR"}
    target_aoi = target_to_aoi[target]

    latency = row["1st_gaze_latency"]

    if (row["Look_before_end_of_label"] not in [target_aoi, "ATT"]) and (latency > 2000):
        return np.nan

    else:
        if row["1st_gaze_after_label"] == target:
            return 1
        elif not row["1st_gaze_after_label"]:
            return np.nan
        else:
            return 0


def _secgaze_validate_onehot(row, target=None):
    """
    first_gaze mean will be:
        nr of trials where first_gaze on target / all_other trial
        all_other trial: on boring or on familiar or on int but latency too high
    """

    if row["2nd_gaze_after_label"] == target:
        return 1
    elif not row["2nd_gaze_after_label"]:
        return np.nan
    else:
        return 0


def get_mean_latency(df):
    """
    returns mean latency of the first gaze where the look at the end of label is on AG.
    only counts latency values < 2050 ms
    """

    df = df[df["Look_before_end_of_label"] == "ATT"]
    # check if latency exists and smaller than 2050 ms
    latency_series = df[df["1st_gaze_latency"] != "-"]["1st_gaze_latency"]
#    latency_series = df[df["1st_gaze_latency"] < 2050]["1st_gaze_latency"]
    mean_latency = latency_series.mean()

    return mean_latency





def print_dataframe(df, filename, sheetname):

    if filename[-4:] != "xlsx":
        filename += ".xlsx"
    excel = os.path.join(dir_name, filename)
    df.to_excel(excel, sheet_name=sheetname)
    print("Dataframe {0} saved to excel.".format(filename))


if __name__ == "__main__":
    main()



