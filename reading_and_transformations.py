# -*- coding: utf-8 -*-
"""
Reading, recoding, tagging, interpolating Tobii T60XL eye tracker data
"""

import pandas as pd
import numpy as np
import math
import swifter


def read_tsv_file(logfilepath):
    """
    Reads datafile, validates format, creates 'gazepoints' column.
    Drops unneded columns.
    Returns dataframe.
    """

    def check_df_format(df):

        cols = ["TimeStamp","GazePointX", "GazePointY"]
        for c in cols:
            if df[c].dtype != float:
                print(f"WARNING! Experiment data has an invalid column: {c}!")
                return None
        return df

    usecols=["TimeStamp", "Event", "GazePointX", "GazePointY"]
    df = (
        pd.read_csv(logfilepath, sep="\t", usecols=usecols, engine="python")
        .pipe(check_df_format)
          )
    df["gazepoints"] = [(x,y) if (x,y) != (-1,-1) else "invalid"
                                          for x,y in zip(df["GazePointX"], df["GazePointY"])]
    df.drop(labels=["GazePointX", "GazePointY"], axis=1, inplace=True)

    return df


def detach_events(df):
    """
    Divides dataframe into a df containing only events and another df containing gaze data
    """

    df_events = df.drop(["gazepoints"], axis=1) # creates a copy
    df_events = df_events[df_events["Event"].notna()]

    df = df[df["Event"].isna()]
    df.drop(labels=["Event"], axis=1, inplace=True)

    return df_events, df


def interpolate_missing_samples(df, freq=60, max_gap_length=101):
    """
    Interpolate small gaps:
        Fill missing datapoints with values calculated from preceding and following datapoint coordinates.
        A gap is to be interpolated if:
        - the gap is smaller than max_gap_length (in ms)
        - there are two-two valid samples on both ends of the gap
    """

    # set new indexes to iterate over while keeping original as a column
    df = df.assign(original_index=df.index, new_index=range(len(df.index)))
    df.set_index("new_index", inplace=True)

    s_gp = df["gazepoints"]

    sample_time = 1000/freq
    max_sample_nr = int(max_gap_length / sample_time) # 6

    startindex = s_gp.index[2]
    lastindex = s_gp.index[-3]

    i = startindex
    while i <= lastindex:

        if s_gp[i] == "invalid":

            counter = 1
            j = i+1
            start = i
            while (j <= lastindex) and (s_gp[j] ==  "invalid"):
                counter += 1
                j = j+1

            if counter <= max_sample_nr:

                # chech for 2-2 valid samples on both ends
                indices_to_check = [start-2, start-1, j, j+1]
                checked_samples = [s_gp[ind] for ind in indices_to_check]
                if "invalid" not in checked_samples:

                    prec_sample = s_gp[start-1]
                    foll_sample = s_gp[j]
                    fill_values = _calculate_fill_values(prec_sample, foll_sample, counter)
                    s_gp[start:j] = fill_values

            i = j+1

        else:
            i = i+1

    df = df.assign(gazepoints = s_gp)
    return df


def _calculate_fill_values(prec_sample, foll_sample, counter):
    """
    Calculates the values to fill a gap with in interpolation.
    """

    x1 = prec_sample[0]
    y1 = prec_sample[1]
    x2 = foll_sample[0]
    y2 = foll_sample[1]
    x_step = (x2-x1)/(counter+1)
    y_step = (y2-y1)/(counter+1)
    fill_x = [x1+c*x_step for c in range(1,counter+1)]
    fill_y = [y1+c*y_step for c in range(1,counter+1)]

    fill_values = list((zip(fill_x, fill_y)))

    return fill_values


def assign_aoi_tags(df, aoi, aoi_ag=None):
    """
    Adds "aoi" column containing an aoi tag for each gazepoint.
    ----------
    aoi: collections.namedtuple
    """

    def gazepoint_to_aoi(gazepoint, aoi, aoi_ag=None):
        """ Checks if the gazepoint is within an AOI and returns the aoi label or the gazepoint."""

        def contains(gazepoint, AOI):
            """ Checks if a pair of coordinates is within an AOI. """

            if gazepoint == "invalid":
                return False

            gpx, gpy = gazepoint[0], gazepoint[1]
            aoix, aoiy = AOI[0][0], AOI[0][1]
            width, height = AOI[1], AOI[2]

            if ((aoix - width/2) <= gpx <= (aoix + width/2) and (aoiy - height/2) <= gpy <= (aoiy + height/2)):
                return True
            else:
                return False


        if contains(gazepoint, aoi.inter):
            return "INT"
        elif contains(gazepoint, aoi.bor):
            return "BOR"
        elif aoi_ag and contains(gazepoint, aoi_ag):
            return "ATT"
        elif aoi.fam1 and contains(gazepoint, aoi.fam1):
            return "FAM"
        elif aoi.fam2 and contains(gazepoint, aoi.fam2):
            return "FAM"
        else:
            return "OUT"


    # add "aoi" columns with aoi tags
    df = df.assign(aoi = df["gazepoints"]
            .swifter.progress_bar(False).apply(gazepoint_to_aoi, args=(aoi,), aoi_ag=aoi_ag).values)

    return df


# TODO
def interpolate_gap_samples(df, freq=60, max_gap_length=101):
    """
    to be defined: interpolates small periods that cut up fixations.
    e.g. "FAM...", "OUT, OUT", "FAM..."
    """
    return df


def calculate_velocity(df):
    """
    Adds velocity column to dataframe.
    Velocity is not calculated at events and in "invalid" datapoints.
    df: dataframe of all subject data without events, with successive indices
    """
    s = df["gazepoints"]

    velocity_values =  pd.Series(data=[np.nan]*len(s.index), index=s.index)
    velocity_values[0] = 0

    for i in s.index[:-1]:

        gazepoint = s[i]

        if gazepoint == "invalid":
            velocity_values[i+1] = "None"

        else :
            x1 = gazepoint[0]
            y1 = gazepoint[1]

            k = i+1
            next_gazepoint = s[k]

            if next_gazepoint == "invalid": # no velo
                velocity_values[k] = "None"

            else:
                x2 = next_gazepoint[0]
                y2 = next_gazepoint[1]

                dist = math.sqrt((x2-x1)**2 + (y2-y1)**2)

                velo = dist / 16.7
                velocity_values[k] = velo

    df = df.assign(velocity = velocity_values)
    return df





