#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Pi-Yueh Chuang <pychuang@gwu.edu>
#
# Distributed under terms of the MIT license.

"""
A Tk GUI for monitoring Azure status.
"""
import sys
import tkinter

class AzureMonitorWindow(tkinter.Frame):
    """The base and frame for printing information."""

    def __init__(self, master=None):
        """__init__"""
        super().__init__(master)
        self.master = master
        self.pack()
        self.init_button()
        self.init_text()

    def init_button(self):
        """Definition of the Quit button."""
        self.button = tkinter.Button(self)
        self.button["text"] = "Quit"
        self.button["command"] = self.master.destroy
        self.button.pack(side="bottom")

    def init_text(self):
        """Initialization of the text section."""
        self.text = tkinter.Text(self, state=tkinter.DISABLED)
        self.text.pack(side=tkinter.LEFT, fill=tkinter.Y)

        self.scrollbar = tkinter.Scrollbar(self)
        self.scrollbar.pack(side=tkinter.RIGHT, fill=tkinter.Y)

        self.text.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.text.yview)

    def update_text(self, s):
        """Update the text inf the text section with s."""
        vw = self.text.yview()
        self.text.config(state=tkinter.NORMAL)
        self.text.delete(1.0, tkinter.END)
        self.text.insert(tkinter.END, s)
        self.text.config(state=tkinter.DISABLED)
        self.text.yview_moveto(vw[0])
