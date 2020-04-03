#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
"""

import pandas as pd
pd.options.mode.chained_assignment = None
import numpy as np
import os
import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from constants import DIR, ST


date = str(datetime.datetime.today().date())

plots_dir = os.path.join(DIR, "time_course", "plots", f"{date}")
try: 
    os.makedirs(plots_dir)
except FileExistsError: 
    pass


# plot one plot
def plot_plotly1(df, label, obj, n):
    
    fig = make_subplots(
    rows=2, cols=1,
    row_heights=[0.2,0.8],
    shared_xaxes=True,
    vertical_spacing=0.03,
    specs=[[{"type": "scatter"}],
           [{"type": "scatter"}]])
    
    upper_bound = go.Scatter(
        name="upper bound",
        x=df["time"],
        y=df["sample_mean"]+df["SE"],
        mode="lines",
        marker=dict(color="#444"),
        line=dict(width=0),
        fillcolor='rgba(68, 68, 68, 0.3)',
        fill='tonexty')

    trace = go.Scatter(
        name="",
        x=df["time"],
        y=df["sample_mean"],
        customdata=df["nr_of_datapoints"],
        hovertemplate = "<b>Proportion</b>: %{y:.2f}"+ 
        "<br><b>Time</b>: %{x}<br>"+ 
        "<b>Datapoints</b>: %{customdata}",
        mode='lines',
        line=dict(color='rgb(31, 119, 180)'),
        fillcolor='rgba(68, 68, 68, 0.3)',
        fill='tonexty')
    
    lower_bound = go.Scatter(
        name="lower bound",
        x=df["time"],
        y=df["sample_mean"]-df["SE"],
        marker=dict(color="#444"),
        line=dict(width=0),
        mode='lines')
    
    # Trace order can be important with continuous error bars
    data = [lower_bound, trace, upper_bound]
    
    layout = go.Layout(
        yaxis=dict(title="Proportion"),
        xaxis=dict(title="Time in ms"),
        title=dict(text=f"<b>{obj} object look in {label} label trials</b> (baseline corrected mean with SE); N <= {n}"+
        "<br>Label onset: x = 0"),
        showlegend = False,
        annotations=[
        dict(
            x=339,
            y=-0.9,
            xref="x",
            yref="y",
            text="Label offset",
            showarrow=True,
            arrowhead=7,
            ax=40,
            ay=0
        )
    ])
    
    fig = go.Figure(data=data, layout=layout)
    
#    last_index = list(df.index)[-1]
#    end_time = df.at[last_index,"time"]
    end_time = df["time"].iloc[-1]
    
    fig.add_shape( # chance line
                type="line",
                name="Chance",
                x0=0,
                y0=0,
                x1=end_time,
                y1=0,
                line=dict(color="Blue", width=3, dash="dot")
                )
                
    fig.add_shape( # end of label
                type="line",
                name="End of label",
                x0=339, # label ends 339 ms (mean) after onset
                x1=339,
                y0=-1,
                y1=1,
                line=dict(color="Green", width=3)
                )
                
#    fig.add_shape( # end of gaze period
#                type="line",
#                name="End of gaze period",
#                x0=2339, # label ends 339 ms (mean) after onset
#                x1=2339,
#                y0=-1,
#                y1=1,
#                line=dict(color="Red", width=3)
#                )
             
    fig.update_shapes(dict(xref='x', yref='y'))
    
    xticks = np.linspace(0,2250,10)
    xticks = np.insert(xticks,2,339)
#    end = df["time"].iloc[-1]
    xticks = np.append(xticks,round(end_time))
    fig.update_xaxes(tickvals=xticks, ticks="outside", tickwidth=2, tickcolor='crimson', ticklen=10)
    
    yticks = np.linspace(-1,1,17)
    fig.update_yaxes(tickvals=yticks, ticks="outside", tickwidth=2, tickcolor='crimson', ticklen=10)
    
    pic = os.path.join(plots_dir, f"{label}_timecourse_{obj}_object_look.html")
    fig.write_html(file=pic)
    fig.show()


# plot two subplots
def plot_plotly2(df, label, obj, n):
    """
    plot 2 suplots:
        upper: valid datapoints (subjects) along the timeline
        lower: proportion of looking data along the timeline
    """
    
    # define time range for x axis
    time_range = df["time"].copy() - 339
    time_range = time_range.append(pd.Series(round(time_range.iloc[-1] + ST)), ignore_index=True)
    
    fig = make_subplots(
    rows=2, cols=1,
    row_heights=[0.2,0.8],
    shared_xaxes=True,
    vertical_spacing=0.03,
    specs=[[{"type": "scatter"}],
           [{"type": "scatter"}]])
    
    ## SUBPLOTS
    # upper subplot
    datapoints = go.Scatter(
            name="",
            x=time_range,
            y=df["nr_of_datapoints"],
            hovertemplate = "<b>Datapoints</b>: %{y}"+ 
                    "<br><b>Time</b>: %{x:.2f} ms<br>",
            mode="lines+markers")
    
    fig.append_trace(datapoints,1,1)
    
    # lower subplot
    upper_bound = go.Scatter(
        name="upper bound",
        x=time_range,
        y=df["sample_mean"]+df["SE"],
        mode="lines",
        marker=dict(color="#444"),
        line=dict(width=0),
        fillcolor='rgba(68, 68, 68, 0.3)',
        fill='tonexty')

    proportion = go.Scatter(
        name="",
        x=time_range,
        y=df["sample_mean"],
        customdata=df["nr_of_datapoints"],
        hovertemplate = "<b>Proportion</b>: %{y:.2f}"+ 
        "<br><b>Time</b>: %{x:.2f} ms<br>"+ 
        "<b>Datapoints</b>: %{customdata}",
        mode='lines',
        line=dict(color='rgb(31, 119, 180)', width=3),
#        line=dict(color="Red", width=3),
        fillcolor='rgba(68, 68, 68, 0.3)',
        fill='tonexty')
    
    lower_bound = go.Scatter(
        name="lower bound",
        x=time_range,
        y=df["sample_mean"]-df["SE"],
        marker=dict(color="#444"),
        line=dict(width=0),
        mode='lines')
    
    # Trace order can be important with continuous error bars
    fig.append_trace(lower_bound,2,1)
    fig.append_trace(proportion, 2,1)
    fig.append_trace(upper_bound,2,1)
    
    ## LAYOUT
    end_time = time_range.iloc[-1]
    timing = str(end_time)[0]+"sec"
    N = df["nr_of_datapoints"].max()
    
    # define shapes
    shapes = [
            dict(type="line", name="chance", x0=-339, x1=end_time, y0=0, y1=0, line=dict(color="Black", width=2, dash="dot"),
                 xref="x1", yref="y2"),
            dict(type="line", name="label onset", x0=-339, x1=-339, y0=-1, y1=1, line=dict(color="Yellow", width=2),
                 xref="x1", yref="y2"),
            dict(type="line", name="label onset", x0=-339, x1=-339, y0=0, y1=n+1, line=dict(color="Yellow", width=2),
                 xref="x1", yref="y1"),
            dict(type="line", name="label offset", x0=0, x1=0, y0=-1, y1=1, line=dict(color="Green", width=2),
                 xref="x1", yref="y2"),
            dict(type="line", name="label offset", x0=0, x1=0, y0=0, y1=n+1, line=dict(color="Green", width=2),
                 xref="x1", yref="y1")]    
    
    fig.update_layout(
            shapes=shapes,
            title=dict(text=f"<b>{obj} object look in {label} label {timing} trials</b>" + 
                       f" (baseline corrected mean with SE)" +
                       f"<br>Upper plot: nr of active looks; N <= {N}"),
            showlegend = False,
            annotations=[dict(x=0, y=-0.9, 
                              xref="x1", yref="y2", 
                              text="Label offset", 
                              showarrow=True, arrowhead=7, 
                              ax=50, ay=0),
                        dict(x=-339, y=-0.8,
                             xref="x1", yref="y2",
                             text="Label_onset+233ms",
                             showarrow=True, arrowhead=7, 
                             ax=70, ay=0)]
                        )
    
    ## AXES
    
    # x axes for upper subplot
    
    # x axes for lower subplot
    xticks = np.linspace(0, round(end_time,-3), 9)
    xticks = np.insert(xticks,0,-339)
    fig.update_xaxes(tickvals=xticks, ticks="outside", tickwidth=2, tickcolor='crimson', ticklen=10)
    fig.update_xaxes(title_text="Time in ms", row=2, col=1)
    
    # y axes for upper subplot
    yticks = np.arange(0,n+1,2)
    fig.update_yaxes(tickvals=yticks, tickmode = 'array', title_text="N", 
                     ticks="outside", tickwidth=2, tickcolor='crimson', ticklen=10, 
                     row=1, col=1)
    
    # y axes for lower subplot
    yticks = np.linspace(-1,1,17)
    fig.update_yaxes(tickvals=yticks, title_text="Proportion", 
                     ticks="outside", tickwidth=2, tickcolor='crimson', ticklen=10, 
                     row=2, col=1)
    
    # save and show plots
    if obj=="TARGET":
        pic_title = f"timecourse_TARGET_vs_distractor_look_in_{label}_label_{timing}_trials_{n}_subjects.html"
    else:
        pic_title = f"timecourse_FAM_objects_vs_New_objects_look_in_{label}_label_{timing}_trials_{n}_subjects.html"
        
    pic = os.path.join(plots_dir, pic_title)
    fig.write_html(file=pic)
    print("plotted")
    fig.show()