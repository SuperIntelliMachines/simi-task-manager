## Insurance Reminder Bot Plan

## Objective

Send automatic reminders to agent after client demos and to customers before and after plan expiry, so follow-ups happen on time and renewals are not missed.

## Project Overview

Insurance reminder bot helps:

* Remind agent to follow up with clients after a demo  
* Remind customers to renew their insurance before and after expiry  
* Make sure no follow-up or renewal is missed  
* Show agent which clients need attention

## Core Features

* Demo entry and tracking 

            Save demo details (agent, client, demo date). 

* Agent follow-up reminder  
   Automatic reminder after X days to ask client decision.  
*  Renewal reminder sequence   
  Automatic reminders at 10, 5, 2 days before expiry, on expiry day, and next day after expiry.   
* Response/status capture   
  Mark outcomes like interested, renewed, not interested, expired.  
* Smart reminder control   
  Avoid duplicate reminders and retry failed messages.   
* Agent monitoring dashboard   
  Track follow-ups, renewals, pending cases

## Technical Stack

* Backend: Python with FastAPI (for APIs and business logic)   
* Scheduler: APScheduler (for sending reminders on schedule)   
* Database: Firestore, PostgreSQL, or MySQL (to store demo, policy, and reminder data)  
* Bot Integration: Telegram Bot API (to send and receive messages)   
* Platform: Google Cloud Run

## Architecture

             ┌─────────────────────┐

             │             Insurance Agent               │

             └─────────┬───────────┘

                                       │

                                       │ Add Demo / Policy Data

                                     ▼

             ┌─────────────────────┐

             │              React Frontend               │

             │          Dashboard / Forms             │

             └─────────┬───────────┘

                                       │ REST APIs

                                      ▼

             ┌─────────────────────┐

             │         FastAPI Backend                 │

             │        Business Logic APIs             │

             └───────┬─────┬───────┘

                                 │              │

     Store Data          │               │ Trigger Reminder Logic

                                │               │

                               ▼              ▼

          ┌─────────────────────┐

          │              PostgreSQL                     │

          │            Agents / Policies               │

          │           Demos / Reminders           │

          └─────────┬───────────┘

                                   │  
    
                                   │ Scheduled Jobs

                                  ▼

          ┌─────────────────────┐

          │ APScheduler/Celery                    │

          │ Reminder Processor                   │

          └─────────┬───────────┘

                                   │

      Send Reminder    │

                                  ▼

          ┌─────────────────────┐

          │   Telegram Bot API                       │

          └─────────┬───────────┘

                                    │

     ┌───────────┴───────────────┐

     ▼                                                                   ▼

┌─────────────────┐          ┌─────────────────┐  
│           Insurance Agent       │          │                Customer            │   
│            Follow-up Alert        │          │             Renewal Alert         │   
└─────────────────┘          └─────────────────┘

### End-to-End Workflow

* Agent logs demo and policy data is stored.  
* Scheduler computes due reminders for both tasks.  
* Bot sends reminders to the right recipient (agent/customer).  
* Responses are captured and status is updated.  
* Dashboard/report shows pending, completed, renewed, expired, and conversion metrics.

Suggested APIs:

* POST /demos/log  
* POST /policies/create  
* GET /reminders/pending  
* POST /reminders/ack  
* GET /reports/insurance-kpis

### Tasks

Task 1 (Agent)

* Trigger: demo logged  
* Recipient: assigned agent  
* Time: demo date \+ X days  
* Message intent: "Please follow up with Client X about the plan decision."

Task 2 (Customer)

* Trigger: policy expiry date  
* Recipient: policyholder (optional copy to agent)  
* Times: expiry-10, expiry-5, expiry-2, expiry day, expiry+1  
* Message intent:"Your policy expires in 10 days. Renew now." "Your plan has expired. Renew immediately to avoid coverage gap."

### Status Logic and Escalations

* If a customer renews, all remaining reminders for that cycle are canceled.  
* If no renewal by expiry+1, create an escalation task for the agent.  
* If the agent marks "not interested" in Task 1, close the lead cycle.  
* If the agent marks "follow-up later," reschedule to the selected date.

### Delivery Plan

Week 1

* Finalize requirements and message templates  
* Build database schema and core APIs

Week 2

* Implement scheduler and Task 1 reminders  
* Capture agent outcomes via bot actions

Week 3

* Implement Task 2 renewal cadence (-10, \-5, \-2, 0, \+1)  
* Add retry, deduplication, and event logging

Week 4

* Build dashboards and KPI reports  
* UAT, production hardening, and go-live

### Go-Live Acceptance Criteria

* All reminder stages trigger correctly in UAT.  
* No duplicate reminders for the same stage and recipient.  
* Responses update status in real time.  
* Dashboard reflects daily business metrics accurately.  
* Runbook documented for support and operations.

