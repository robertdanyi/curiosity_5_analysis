#!/usr/bin/env python3
# -*- coding: utf-8 -*-



# sample time: 1000ms/60
freq = 60 # monitor refreshment rate (Hz / fps)
ST = 1000/freq # 16.66667 ms
        
        
def collect_gaze(df,  collect_init_look=True, freq=60, threshold=134):
    """
    Transforms a dataframe to a Gaze object.

    parameters:
        df: a slice of the original big dataframe
        freq: refresh rate of the eye tracker data collection
        threshold: minimum nr of frames/datapoints of a gaze


    def.: 'gaze': continuous look on one of the objects for a period larger then a given threshold

    label onset: both: 2100ms, End of label: 'tacok': 2680ms; 'bitye': 2620 ms. mean: 2650ms. -> 550ms but ATT is still there until 160x16.7= 2672ms
    response latency: 233ms - 2000ms, from target label (stop closure) onset + duration of eye movement (?)
    -> if starts fixating on one of the objects before 233ms after label onset (minimum latency to initiate a saccade in response to a peripheral target),
    = 2333 ms after start of labeling/ATT, then it isn't a first look. -> 2672-2333=-339=-340ms
    (shall we use 367 ms?)

    variables:
        gaze_list: list of lists of successive gazepoints ('hits') within the same aoi,
            where len(hits) >= min_sample_nr
        tag_time_dur_dict: dictionary of the form {rank:[tag, (starting) time, duration (lenght)]}

    Returns
        a Gaze() object
    """

    sample_time = 1000/freq # 16.7 ms
    min_sample_nr = int(threshold / sample_time) # 8 samples at 134 threshold

    gaze_list = [] # list of hit lists

    hits = [] # first element is timestamp of gaze start, rest are look tags.
    for i in df.index:

        look = df.at[i, "aoi"]

        if look != "OUT":

            if not hits: # empty hits list
                latency = df.at[i, "TimeStamp"] #- start
                hits.append(latency)
                hits.append(look)

            elif look in hits:
                hits.append(look)
                # if last row:
                if (i == df.index[-1]) and (len(hits) > min_sample_nr): # time is also in the hits
                    gaze_list.append(hits[:])

            else: # new aoi tag
                if len(hits) >= min_sample_nr:
                    gaze_list.append(hits[:])

                hits[:] = []
                latency = df.at[i, "TimeStamp"] #- start
                hits.append(latency)
                hits.append(look)

        else:
            if len(hits) > min_sample_nr:
                gaze_list.append(hits[:])
            hits[:] = []

    # tag_time_dur_dict: {rank:[tag, time, duration (lenght)]}
    tag_time_dur_dict = {}
    for i,gaze in enumerate(gaze_list):

        tag_time_dur_dict[i+1] = [gaze[-1], gaze[0], len(gaze[1:])]

    gaze_coll = GazeCollection(tag_time_dur_dict)

    return gaze_coll


class GazeCollection:
    """
    Creates an object with a dictionary as instance variable.

    tag_time_dur_dict: {rank:[tag, (starting) time, duration (lenght)]}
    """

    def __init__(self, tag_time_dur_dict):
        self._dict = tag_time_dur_dict


    def get_taglist(self):
        """ Returns the tags in the gaze object """

        taglist = []
        for v in self._dict.values():
            taglist.append(v[0])

        return taglist


    def get_last_gaze(self):
        """
        start of period: att gett start
        end of period: end of initial gaze (> 2672)
        start time should be above 2333ms (onset:2100, min. time needed to initialise gaze shift: 233)
        
        """

        gaze_nr = list(self._dict.keys())[-1]
        gaze_data = self._dict[gaze_nr]
        latency = gaze_data[1]
        
        return gaze_data[0], latency, gaze_data[2]


    def get_gaze_data(self, gaze_nr, start_time=0):
        """ Returns the tag, time, duration for a given rank key"""

        if gaze_nr not in self._dict.keys():
            return None, None, None

        else:
            gaze_data = self._dict[gaze_nr]
            latency = gaze_data[1] - start_time
            if latency > 2000:
                return None, None, None
            else:
                return gaze_data[0], latency, gaze_data[2]


    def sort_gaze(self, nr_of_gazes=3, start_time=0):
        """
        Creates nested dictionary (for multi-index columns df)
        from the gaze data of the trial
        returns dictionary
        """

        l = ["Initial gaze", "1st gaze", "2nd gaze", "3rd gaze"]
        outer_keys = l[:nr_of_gazes]
        inner_keys = ["object","latency","duration"]
        d = {(outer, inner):None for outer in outer_keys for inner in inner_keys}
        
        keys = outer_keys[1:]
            
        # check if first gaze is initial gaze
        tag, latency, duration = self.get_gaze_data(gaze_nr=1, start_time=start_time)
        if (not latency):
            return d 
        
        if latency < 33:
            print("Initial gaze...")
            # shift data
            for i, k in enumerate(outer_keys):
                tag, latency, duration = self.get_gaze_data(gaze_nr=i+1, start_time=start_time)
                d[(k,"object")]=tag
                d[(k,"latency")]=latency
                d[(k,"duration")]=duration * ST if duration else None
        else:
            for i,k in enumerate(keys): # 0th gaze not filled
                tag, latency, duration = self.get_gaze_data(gaze_nr=i+1, start_time=start_time)
                d[(k,"object")]=tag
                d[(k,"latency")]=latency
                d[(k,"duration")]=duration * ST if duration else None
            
        return d            


    # unused
    def get_first_gaze(self):
        """
        Returns the tag, time, duration of the first gaze, if there is one
        First gaze: the first fixation that starts between response start and response end
        0 latency would be label onset. Min 233 ms latency to account for the time needed to initialise response.
        """

        response_start = 233
        response_end = 2572

        for nr, gaze_data in self._dict.items():

            if (gaze_data[1] >= response_start) and (gaze_data[1] < response_end):

                return gaze_data[0], gaze_data[1], gaze_data[2] # first gaze

        return None, None, None


    def calculate_onobject_gaze(self):
        """
        Adds the durations (lenghts) of the gazes directed at the same object.

        all_gaze: the sum of gazes directed at all the (interesting, boring and familiar) objects.

        Returns
            cumulative gaze of each object kind proportional to all_gaze
        """
        onint_gaze, onboring_gaze, onfam_gaze = 0,0,0
        for k, v in self._dict.items():
            if v[0] == "INT":
                onint_gaze += v[2]
            elif v[0] == "BOR":
                onboring_gaze += v[2]
            elif v[0] == "FAM":
                onfam_gaze += v[2]

        all_gaze = onint_gaze + onboring_gaze + onfam_gaze
        onint = onint_gaze / all_gaze if all_gaze != 0 else 0
        onboring = onboring_gaze / all_gaze if all_gaze != 0 else 0
        onfam = onfam_gaze / all_gaze if all_gaze != 0 else 0

        return onint, onboring, onfam



def calculate_onscreen_gaze(dataframe, start_times, end_times):
    """ returns a list of proportional looking times on screen for each trial"""

    onscreen_looks = []

    for n in range(len(start_times)):
        df = dataframe[(dataframe["TimeStamp"] >= start_times[n]) & (dataframe["TimeStamp"]< end_times[n])]
        valid_times = df["gazepoints"].apply(lambda x : x != "invalid").sum()
        onscreen_looks.append(valid_times / df["gazepoints"].size)

    return onscreen_looks

