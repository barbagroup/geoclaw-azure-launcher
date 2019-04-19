#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Pi-Yueh Chuang <pychuang@gwu.edu>
#
# Distributed under terms of the BSD 3-Clause license.

"""
A callable object of graphical real-time status monitor.
"""
import functools
import numpy
from matplotlib import pyplot
from matplotlib import animation


class GraphicalMonitor():
    """A callable object of graphical real-time status monitor."""

    def __init__(self):
        """Constructor."""

        # figure object and axes objects
        self._fig = self._ax_nodes = self._ax_tasks = None

        # the candidate labels for nodes with a preferred order
        self._label_candidates = [
            "running", "idle", "creating", "starting", "waiting_for_start_task",
            "unusable", "leaving_pool", "rebooting", "reimaging",
            "start_task_failed", "unknown", "offline", "preempted"]

        # the task status in our preferred order
        self._task_status_labels = ["succeeded", "running", "active", "failed"]

    def __call__(self, mission, reporter, interval=30):
        """Make this class callable.

        Args:
            mission [in]: a MissionInfo object.
            reporter [in]: a MissionStatusReporter object.
            interval [in]: interval to update status (in seconds).
        """

        # figure object and axes objects
        self._fig, [self._ax_nodes, self._ax_tasks] = pyplot.subplots(
            num=1, figsize=(7, 9), dpi=100,
            nrows=2, ncols=1, sharex=False, sharey=False, squeeze=True,
            gridspec_kw={"left": 0., "right": 1., "top": 0.95, "bottom": 0.})

        # generator
        generator = functools.partial(reporter.status_generator, mission)

        # animation
        ani = animation.FuncAnimation(
            self._fig, self._animate, frames=generator, interval=interval*1000)

        # pop up a window of animation
        pyplot.show()

        self._fig = self._ax_nodes = self._ax_tasks = None

    def _animate(self, status):
        """The function being called by matplotlib for every frame.

        Args:
            status [in]: the dictionary returned by reporter's status_generator.
        """

        self._update_ax_nodes(
            status["timestamp"], status["pool_status"],
            status["allocation_status"], status["node_status"])

        self._update_ax_tasks(
            status["timestamp"], status["job_status"], status["task_status"])

    def _update_ax_nodes(self, timestring, pool_s, allocation_s, node_s):
        """Update the axes object of node information.

        Args:
            timestring [in]: timestamp of when the status data was obtained.
            pool_s [in]: pool status
            allocation_s [in]: allocation status
            node_s [in]: status of nodes
        """

        self._ax_nodes.clear()

        # initialize empty lists
        data = []
        labels = []
        texts = []

        for label in self._label_candidates:
            if node_s[label] > 0:
                data.append(node_s[label])
                labels.append(label)
                texts.append("{}: {}".format(label, node_s[label]))

        # the text at the center of the donut
        if pool_s == "N/A":
            center_text = "Not available"
        else:
            center_text = \
                "Pool: {}\nAllocation: {}\nTotal nodes: {}".format(
                    pool_s, allocation_s, sum(data))

        # title
        title = "Node status at {}".format(timestring)

        # call the underlying donut drawer
        self._donut_drawer(
            self._ax_nodes, data, labels, texts, title, center_text)

    def _update_ax_tasks(self, timestring, job_s, task_s):
        """Update the axes object of task information.

        Args:
            timestring [in]: timestamp of when the status data was obtained.
            job_s [in]: job status
            task_s [in]: status of tasks
        """

        self._ax_tasks.clear()

        # initialize empty lists
        data = []
        texts = []

        for label in self._task_status_labels:
            data.append(task_s[label])
            texts.append("{}: {}".format(label, task_s[label]))

        # the text at the center of the donut
        if job_s == "N/A":
            center_text = "Not available"
        else:
            center_text = "Total: {}".format(sum(data))

        # title
        title = "Task status at {}".format(timestring)

        # call the underlying donut drawer
        self._donut_drawer(
            self._ax_tasks, data, self._task_status_labels,
            texts, title, center_text)

    def _donut_drawer(self, ax, data, labels, texts, title, center_text):
        """Underlying drawing function for the donut chart.

        Args:
            ax [in]: axes object.
            data [in]: data for the pie/donut chart.
            labels [in]: labels for values in the data.
            texts [in]: texts used in the text boxes of data.
            title [in]: title for this axes.
            center_text [in]: text in the center blank area of the donut chart.
        """

        if sum(data) == 0:
            data = [1]
            labels = ["No data available"]
            texts = ["No data available"]

        # create a donut-like pie chart centered at (x, y) = (0, 0) with r = 1
        wedges, _ = ax.pie(data, wedgeprops={"width": 0.5}, startangle=90)

        # the properties for the bounding box of an annotation
        bbox_props = {"boxstyle": "square, pad=0.3", "fc": "w", "ec": "k", "lw": 0.72}

        # loop through all wedges and add an annotation to each of them
        for i, w in enumerate(wedges):

            if data[i] == 0:
                continue

            # the angle of the center line of the wedge
            ang = (w.theta2 + w.theta1) / 2.

            # the data point where the annotation refers to
            # also the start of the connecting line
            xy = (numpy.cos(numpy.deg2rad(ang)), numpy.sin(numpy.deg2rad(ang)))

            # the location of the annotation box
            # also the end of the connecting line
            xytext = (1.05*numpy.sign(xy[0]), 1.05*xy[1])

            # which side the text shoulf align to is based on if it's on left/right
            ha = {-1: "right", 1: "left"}[int(numpy.sign(xy[0]))]

            # properties of the connecting line
            if (ang % 180) == 0:
                connectionstyle = "arc3, rad=0"
            else:
                connectionstyle = "angle, angleA=0, angleB={}".format(ang)

            ax.annotate(
                texts[i], xy=xy, xytext=xytext, bbox=bbox_props, va="center", ha=ha,
                arrowprops={"arrowstyle": "-", "connectionstyle": connectionstyle})

        # center text, title, y limits, legends
        ax.annotate(center_text, xy=(0, 0), xytext=(0, 0), va="center", ha="center")
        ax.set_ylim(-1.2, 1.4)
        ax.legend(wedges, labels, ncol=len(labels), loc=9, bbox_to_anchor=(0.5, 1.0))
        ax.set_title(title)
        ax.axis("off")

if __name__ == "__main__":
    import argparse
    from user_credential import UserCredential
    from mission_info import MissionInfo
    from mission_status_reporter import MissionStatusReporter

    parser = argparse.ArgumentParser(
        description="Graphical monitor of Azure batch pool and job")

    parser.add_argument(
        "missionname", metavar="mission-name", action="store", type=str,
        help="Name of the miission.")

    parser.add_argument(
        "credential", metavar="credential-file", action="store", type=str,
        help="An encrpyted file of Azure Batch and Storage credentials.")

    parser.add_argument(
        "passcode", metavar="passcode", action="store", type=str,
        help="Passcode to decode credential file.")

    parser.add_argument(
        "--interval", metavar="seconds", action="store", type=int, default=30,
        help="Seconds between status updates. (default: %(default)s)")

    args = parser.parse_args()

    # dummy MissionInfo object (only providing the name of the mission)
    info = MissionInfo(args.missionname)

    # UserCredential object
    cred = UserCredential()
    cred.read_encrypted(args.passcode, args.credential)

    # MissionStatusReporter
    reporter = MissionStatusReporter(cred)

    # GraphicalMonitor
    monitor = GraphicalMonitor()
    monitor(info, reporter, args.interval)
