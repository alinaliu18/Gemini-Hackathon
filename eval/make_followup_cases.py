"""Writes eval/followup_cases.jsonl: 45 candidate answers labelled with what a follow-up should ask about.
The answers and labels were written by the developer, not by an interviewer. Run from the repo root."""
import json
ORDER = ("example", "own_action", "result_number")  # pipeline/followup.py MISSING
Q = {
 "pm": "Tell me about the course planning app on your resume. What did you decide and why?",
 "lead": "You led the hackathon team. How did you handle a disagreement on the team?",
 "res": "Tell me about the user research you did for the club website.",
 "fail": "Tell me about a project that did not go the way you planned.",
 "data": "Walk me through the data analysis you did in your internship.",
 "club": "Why do you want to join our consulting club?",
 "conf": "Describe a time you had to learn something quickly.",
 "pri": "How do you prioritize when you have too much to do?",
 "cust": "Tell me about a time you dealt with a difficult customer or user.",
}
# (question key, answer, expected missing in asking order: own_action, result_number, example)
C = [
 # nothing missing: own action, a number, one specific situation -> next
 ("pm","In spring I noticed students kept missing prerequisite deadlines, so I proposed a warning on the planner page. I sketched it, ran five user calls, and convinced our engineer to build it in a week. After launch, missed-prerequisite errors dropped from 40 a week to 12.",[]),
 ("lead","During the Gemini hackathon two teammates wanted to rebuild the camera feature at 2 am. I pulled up the judging rubric, showed that the demo flow was worth twice as many points, and asked each of them to own one screen. We finished the demo with 45 minutes to spare and placed third out of 32 teams.",[]),
 ("res","Last October I interviewed 8 members who had left the club. I wrote the interview guide and did all 8 calls myself. Six of them said they never found the event calendar, so I moved it to the home page, and event sign-ups went up 30 percent the next month.",[]),
 ("fail","My first internship project was a churn model that I promised in three weeks. I underestimated cleaning the data and missed the deadline by 10 days. I told my manager in week two, cut the scope to one region, and the reduced model still caught 70 percent of the accounts that churned.",[]),
 ("data","At the startup I owned the weekly retention report. I wrote the SQL, found that one cohort was double counted, and fixed the join. The corrected numbers showed retention was 18 percent, not 26, which changed how the team planned the next quarter.",[]),
 ("conf","Two weeks before my data structures final I had to learn dynamic programming from scratch. I did 3 problems a day from a list I built myself and explained each one out loud to a friend. I went from failing the practice exam to a 91 on the final.",[]),
 ("pri","Last finals week I had two exams, a club event, and a part-time shift. I listed every task with its deadline, moved my shift by asking a coworker to swap, and told the club I could only run the sign-in table. I finished all four and got an A minus in both exams.",[]),
 ("cust","At the campus bookstore a parent was angry that a textbook was out of stock the day before class. I checked the other two campus stores, found one copy, and walked it over myself on my break. She came back the next week and left a 5 star review naming me.",[]),
 ("club","Last year I did a case competition with three friends and I built the market sizing for a coffee chain expansion. We came second out of 20 teams, and I realized I liked structuring messy problems more than anything in my classes. That is why I want the training your club runs.",[]),
 ("pm","I decided to drop the social feed from the app. I looked at our analytics and only 3 percent of users opened it, while 60 percent used the schedule view daily. I wrote the proposal, presented it to the team on a Friday, and we cut it the next sprint, which saved about two weeks of work.",[]),
 ("data","For my capstone I analyzed 2 years of bike share data. I built the cleaning pipeline in pandas and found that 15 percent of trips were maintenance moves. Removing them changed which stations looked busiest, and the city used my station ranking in their spring planning memo.",[]),
 ("lead","When our designer and engineer argued over a login screen in the hackathon, I asked each to show me one user who would be hurt by the other's version. Neither could, so I picked the simpler one, and we saved about 3 hours that went into the demo.",[]),
 ("res","For the club website I ran a survey of 120 members myself and then did 5 follow-up interviews. I found that most people only visited to check the meeting room, so I put the room and time at the top. Visits to the events page fell, but questions in the group chat dropped by half.",[]),
 ("conf","My first week at the internship I was asked to use dbt, which I had never seen. I read the docs that night, rebuilt one existing model myself to learn it, and shipped my first model on day 4. My manager said that was the fastest onboarding on the team that year.",[]),
 ("cust","A user emailed our app support saying we had deleted her schedule. I answered her within an hour, found in the logs that she had two accounts, and merged them myself. She replied that it was fixed, and I wrote a help article that cut those tickets from 9 a month to 2.",[]),
 # missing own_action only: team words, has number and specific situation
 ("pm","In winter quarter the team decided to add prerequisite warnings to the planner. We ran user calls and the engineers built it in a week. After launch missed-prerequisite errors dropped from 40 a week to 12.",["own_action"]),
 ("lead","In the hackathon there was a fight about rebuilding the camera feature at 2 am. The team looked at the rubric and decided to focus on the demo instead. We finished with 45 minutes to spare and placed third out of 32.",["own_action"]),
 ("res","Last October our club interviewed 8 members who had left. Most of them never found the calendar, so the website team moved it to the home page and sign-ups rose 30 percent.",["own_action"]),
 ("data","At the startup the analytics team found a double count in the weekly retention report in March. Once it was fixed, retention was 18 percent instead of 26, and the company changed its plan for the next quarter.",["own_action"]),
 ("cust","At the bookstore last fall a parent was angry that a textbook was out of stock. Our store found a copy at another campus location and it got delivered that afternoon. She later left a 5 star review.",["own_action"]),
 ("fail","Our churn model project last summer missed its deadline by 10 days because the data was messy. The team cut the scope to one region and the smaller model still caught 70 percent of churned accounts.",["own_action"]),
 ("club","Last year my group entered a case competition about a coffee chain expansion. The group's market sizing got us second place out of 20 teams, and that experience is why I want to join.",["own_action"]),
 # missing result_number only: own action, specific, result only in words or no result
 ("pm","In spring I noticed students kept missing prerequisite deadlines, so I proposed a warning on the planner page. I sketched it, ran user calls, and convinced our engineer to build it. After launch it worked really well and people liked it.",["result_number"]),
 ("lead","During the hackathon two teammates wanted to rebuild the camera feature at 2 am. I pulled up the judging rubric and showed them the demo mattered more, and I asked each of them to own one screen. It went pretty smoothly after that.",["result_number"]),
 ("res","Last October I interviewed members who had left the club. I wrote the guide and did the calls myself. Many of them never found the calendar, so I moved it to the home page, and engagement improved a lot.",["result_number"]),
 ("data","At the startup I owned the weekly retention report. I wrote the SQL myself and found one cohort was double counted, so I fixed the join. The corrected numbers were quite different and leadership was surprised.",["result_number"]),
 ("conf","Before my data structures final I had to learn dynamic programming quickly. I made my own problem list and explained each problem out loud to a friend every night. By the final I felt much more confident.",["result_number"]),
 ("cust","At the bookstore a parent was upset that a textbook was out of stock the day before class. I called the other campus stores, found a copy, and walked it over myself on my break. She was really happy in the end.",["result_number"]),
 ("fail","For my first internship project I promised a churn model too quickly. I told my manager early that I would be late, cut the scope to one region myself, and delivered the smaller version. It turned out okay.",["result_number"]),
 # missing example only: own action words but general, habit talk
 ("pri","I usually make a list of everything and sort it by deadline. I always tell people early if I can't do something, and I try to protect time for the most important work first.",["example","result_number"]),
 ("conf","I'm the kind of person who learns fast. Whenever I need to pick something up, I read the documentation, build a small project myself, and ask people questions until it clicks.",["example","result_number"]),
 ("cust","I generally stay calm with difficult people. I listen first, I repeat back what they said, and then I try to find a fix myself instead of passing them to someone else.",["example","result_number"]),
 ("lead","When there is a disagreement I tend to bring people back to the goal. I ask each person to explain their reasoning and then I make a call if we are stuck.",["example","result_number"]),
 ("club","I want to join because I love solving business problems and I enjoy working with smart people. I'm always reading about companies and I think consulting fits how I think.",["example","result_number"]),
 ("fail","Projects don't always go to plan, and when that happens I usually reset the scope and communicate early. I think being honest about delays is the most important thing.",["example","result_number"]),
 # two or three missing: asked in order own_action, result_number, example
 ("pm","The team decided to add warnings to the planner and it worked really well.",["own_action","result_number"]),
 ("lead","We usually talk it out as a team and it tends to work out fine.",["own_action","result_number","example"]),
 ("res","Our club did some interviews with members and the website got better after that.",["own_action","result_number"]),
 ("data","The data team cleaned the retention data and found some errors, and the report became more accurate.",["own_action","result_number"]),
 ("pri","I always prioritize by deadline and it usually works.",["result_number","example"]),
 ("conf","I learn quickly in general. I just read a lot and practice, and it usually goes fine.",["result_number","example"]),
 ("cust","We always try to keep customers happy at the store, and the team handles complaints well.",["own_action","result_number","example"]),
 # answers to a follow-up: judged on the whole exchange so far (main answer plus follow-up answer)
 ("pm","The team decided to add prerequisite warnings to the planner. [Follow-up asked what I did] I ran the five user calls myself and wrote the spec the engineer built from. After launch missed-prerequisite errors went from 40 a week to 12.",[]),
 ("res","Last October our club interviewed members who had left, and the website team moved the calendar. [Follow-up asked what I did] I wrote the guide and ran all 8 calls myself. [Follow-up asked about the result] Sign-ups went up 30 percent the next month.",[]),
 ("lead","During the hackathon I asked each teammate to own one screen after a fight about the camera feature at 2 am. [Follow-up asked what changed] It went pretty smoothly and everyone was happier.",["result_number"]),
]
assert len(C) == 45, len(C)
with open("eval/followup_cases.jsonl", "w") as f:
    for i, (q, a, m) in enumerate(C, 1):
        f.write(json.dumps({"id": f"f{i:02d}", "question": Q[q], "answer": a, "followups_asked": 1 if "[Follow-up" in a else 0,
                            "missing": m, "expected": "follow_up" if m else "next", "expected_first": next((x for x in ORDER if x in m), None)},
                           ensure_ascii=False) + "\n")
from collections import Counter
print(Counter(next((x for x in ORDER if x in m), "next") for _,_,m in C))
