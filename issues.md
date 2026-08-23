1. [FIXED] when i ask for rank it can't answer it: but the csv contains rank:form_no,rank,name,gender,district,sno,remarks: its response
```
To provide you with accurate information, I would need the specific form number of the candidate who scored rank 13 in the 2083 entrance examination. The pass list lookup functionality allows us to verify this directly from the published results.

If you have the form number or any other details, please share them so I can perform a pass list lookup for you. If you do not have the form number, visiting the IOE website at [https://entrance.ioe.edu.np](https://entrance.ioe.edu.np) might help you find this information.

If no specific form number is provided, I cannot determine who scored rank 13 based on the available data. Please let me know if you have any additional details or if there's another question I can assist with.
```

2. [FIXED] it is unsure about today'date and hallucinates and gives fake dates both in english and nepali (bs and ad) we might need to add a date tool so it knows today's date and can answer question based on inferencing date: like it already happened, its in this much days. (i dont mean it should say it in every answer, just a capability for our rag bot) a date tool

```
what is today s date
Today's date in Nepal is **2083 Shrawan 9 (2026-07-15)**.

If you need this information for a specific application or process, it's always a good idea to verify with the official IOE website or the entrance examination board.
```

3. [FIXED] the ui should be more similar to government websites or ioe/tu/pcampus website, a formal educational institutioal vibe. i think the ui should be more welcoming. yeah the chabot is the main attractino but, we should display relevant notices from all sites, like tu, ioe, pcampus, other contituent campus, exam.ioe.edu.np, also think of adding other features to the app that makes it feel like a real product instead of just a ragbot. (admin side where they can upload the tranlsted docuemjtns, and it goes stays there where he can update the bot from the ui? is it possible???)

4. kv cache
5. [FIXED] add citations
6. [FIXED] support markdown formatting in answers
7. [SATISFIED] ui rework
8. remove unnecessary things, keep things that adds value, rethink on app's scope, extend to other campus or be limited to pulchowk, add more information to make the bot more robust
9. Guide the bot to answer smartly to answers
10. play around with the bot for flaws and fix it.
11. [FIXED] add a chat history on the left sidebar, make all three divs seperatly scrollabale, chat, notices and chat-history !
12. [FIXED] include valid citations only, citations for relevant questions and not for out of scope questions, not necessary to mention 4 sources always, just mention where its from.
13. [BUILT] should we add internet search tool? if added what should it use internet for, because we have to provide relevant information from our own docuemnt chunks, what usefulness will a internet search tool have?

    **No general web search. Yes to a notice-fetch tool over the sites we already scrape.**

    Measured against the live bot on 2026-08-23:

    - Asked "is there any new notice published this week", it answered "there is no new
      official notice published specifically for this week" — while the rail beside it
      was showing one published the day before. 35 notices in cache, newest 2026-08-22.
      `notices.py` already scrapes 4 sites; `graph.py` simply cannot see the cache. Not
      an internet gap.
    - Asked the fee for BE Civil at Thapathali, it punted to a link. Section 9 of the
      booklet answers it — the fee table is IOE-wide, not per-campus (Regular NPR
      6,974/sem, 55,792 over 8 semesters). Search would have hidden a retrieval bug
      behind a plausible web answer.
    - Asked when Kathmandu University holds its entrance exam, it gave IOE's date as
      KU's. Search would turn that from wrong-and-ungrounded into wrong-with-a-citation,
      which is exactly what the citation gate in 12 exists to prevent.

    So the tool to build is a fetch, not a search:

    a. Index the *bodies* of the notices we already list, not just their titles. Bounded
       set, known domains, authoritative. Closes the "no new notice" lie.
    b. Sources to cover every constituent campus, not just Pulchowk — Thapathali,
       Purwanchal, Pashchimanchal, Chitwan — since the question is about admission and
       admission happens at all of them. More sources to be added over time.
    c. Refresh on demand during a chat when the cache is stale, rather than waiting for
       the daily cron: a student asking at 4pm about a list published at 2pm should get
       it. Cron stays as the floor, the chat path can trigger a fetch above it.
    d. A staleness guard: let the bot compare the newest notice against its own document
       set and say "6 notices are newer than my documents, here they are" instead of
       denying they exist.

    Open web search stays out. The product's promise is that answers come from the
    official notices; a general search tool dissolves that promise, and the honest
    failure mode of a grounded bot ("I don't have that") is worth more than a confident
    answer from a source nobody vetted.

    **Built 2026-08-23.** One change to the plan, forced by measurement: (a) indexes the
    notice *record* -- title, both dates, publisher, link -- not the notice page. Sampling
    one page per source, every one was a heading over a scanned PDF; the richest held 209
    characters, most of it "Click Here" and "in pdf format". Indexing that would have put
    site chrome into the index to compete with the translated documents, at one HTTP
    request per notice. Worth revisiting only if a source starts publishing real HTML.

    Sources went from 4 to 6: added Pashchimanchal (wrc.edu.np) and Purwanchal
    (ioepc.edu.np). Thapathali renders its notice list in the browser -- its served HTML
    contains no notice at all -- so it needs a headless browser, which is not worth a
    dependency yet. Chitwan publishes no feed and links to tu.edu.np, already a source.
    Note that cec.edu.np is *not* Chitwan Engineering Campus; the campus is cec.tu.edu.np.

    Result: 57 notices from 6 sources, 57 records indexed. "Is there any new notice this
    week" now lists today's two with links instead of denying they exist.
14. [FIXED] there is a bug, whenever i refresh, the latest query reruns again. its because user query is passed through search params, which is why! it's not the case in major chatbots, how do they handles this, and can we move to that system to fix this bug! also creating new chat history every time i refresh for the same question.
15. [FIXED] i kinda don't like the current 3 layout strcutre, we can expand the chat window a little and push the notiecs to right, and without the limiting right border.(the left margin is the sweet spot, we should expand the second layer so that, the right margin equals left margin for the outer container that contains three layers(chatbot, history and notices, and remove the right border from the notices))
16. [FIXED] Let's add one theme color, it looks so off with just black and white
17. [FIXED] bug: when it's generating an answer, an i scroll up, it goes back to the answer streams, which is kinda bad ux. fix it!
18. [FIXED] issue 17 fixed but created a new error: answer doesnot stream properly or not visible, becuase its stuck and the page doesnot auto scroll to bottom while the answer is generating, the user themself has to do it.
19. when i asked it to speak in nepali, it started talking in hindi. so we should strictly make the bot speak in english only. it is incapable of speaking other languages properly. 
20. the whole app still looks black and white, need to include the theme color more!!