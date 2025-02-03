This repo is used to run a league for students' Connect4 agents.

- It is going to be deployed on the Hydra cluster in a screen session, where 
we'll keep a container running. 

- Every couple of hours, it will check if there are any new agents.

- If there are, it will download the code from the cloud, build the container


### Ideas




### Questions

- How to run the tournament from a python file? I don't want to block resources, 
so I need to find a way to launch processes at specific times.

- What to run? Games with empty boards (each agent starts once) and games with 
random starting positions?

- We need code to run the league

- What to store from games and how? Maybe it would be useful to have one
database with all the raw info and then have code that reads that out.
