# (c) Incomplete and conflicting details

_Simulated via `sim/chat_sim.py --mode scripted` — **not a real Vapi call**. See README 'Vapi Setup Steps' for running real calls._

**Scenario:** Customer gives a vague budget answer (ask once more, then move on per the hard rule) and later contradicts their stated age by mentioning they're retired — assistant must confirm, not silently pick one.

## Transcript

**Assistant:** And roughly what monthly budget did you have in mind?

**Customer:** I'm not sure, maybe something reasonable?

**Assistant:** No problem — even a rough monthly figure would help. Any ballpark?

**Customer:** I really don't know, sorry.

**Assistant:** That's alright, we can figure that out later. Could I ask your age?

**Customer:** I'm 25.

**Assistant:** Thanks. And do you have any current health cover?

**Customer:** Well, I'm retired now, so I get some cover through my pension.

**Assistant:** I want to make sure I have this right — you mentioned you're 25, but also that you're retired. Could you confirm which applies?

**Customer:** Sorry, I meant my mother's situation — I'm actually 58 and retired myself.

> 🔧 **score_lead**(`{"age": 58, "city": null, "family_size": null, "conditions": null, "budget": null, "intent": "exploring"}`) → `{"temperature": "cold", "points": 0, "reasons": ["Age 58 is in the senior underwriting range (55-65).", "Budget not provided \u2014 no budget-based scoring applied.", "Family size not provided \u2014 no cross-sell scoring applied.", "No pre-existing conditions disclosed.", "Customer intent (exploring) is neutral/undecided."]}`
