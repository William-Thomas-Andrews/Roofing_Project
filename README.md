# Roofing Project

This repository holds the code I worked on for the startup company Compliancy. Unfortunately I did not upload this to github initially so there are no past versions available. There was a lot of trial and error and much more code than this. Even though my internship is done, I will still keep working on this problem and now upload the changes here.

Project Description: Compliancy is a startup company based in the Miami-Dade and Broward county area in Florida, and it is their goal to help roofers pull permits faster. There are municipality websites that hold roofing permits which are often changed without notice. This makes trouble for roofers and slows down their process. My task was to create a program that checked if these certain pdfs had changed, and if so, change them, and if not, do nothing.

With asynchronous requests, the pdf searching is sufficient and not a long process, and the target links (the pdfs we originally had) can be matched to their scraped counterparts and similiarities found with cosine similarity scores. Next steps: get all target pdfs into accessible form in files with their links (we don't have the links, but we have the pdfs in files), and then write code to read in those pdf text files into the target dictionary, then compare with our scraped resulting dictionary. T
