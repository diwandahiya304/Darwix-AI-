# (a) Cooperative customer

_Simulated via `sim/chat_sim.py --mode scripted` — **not a real Vapi call**. See README 'Vapi Setup Steps' for running real calls._

**Scenario:** Customer answers every qualification question directly and agrees to a next step. Expected: full qualification flow, score_lead called once, create_lead called once, next step agreed and closed warmly.

## Transcript

**Assistant:** Hi, this is Asha calling from Acme Insurance — do you have a moment?

**Customer:** Sure, go ahead.

**Assistant:** Great, thank you. This call is recorded for quality and training purposes. I'm calling about health insurance options — could I ask a few quick questions?

**Customer:** Yes, that's fine.

**Assistant:** Could I start with your age?

**Customer:** I'm 34.

**Assistant:** And which city are you in?

**Customer:** Bangalore.

**Assistant:** How many people are in your family who'd need cover?

**Customer:** Four — myself, my spouse, and two kids.

**Assistant:** Do you or any family member have any pre-existing conditions you'd like to disclose?

**Customer:** No, we're all healthy.

**Assistant:** And roughly what monthly budget did you have in mind?

**Customer:** Around 2000 rupees a month.

**Assistant:** Do you have any current health insurance cover?

**Customer:** No, we don't have any right now.

> 🔧 **score_lead**(`{"age": 34, "city": "Bangalore", "family_size": 4, "conditions": null, "budget": 2000, "intent": "interested"}`) → `{"temperature": "hot", "points": 5, "reasons": ["Age 34 is within the ideal range (<= 55).", "Budget 2000 comfortably covers standard plans (>= 1500).", "Family size 4 meets the cross-sell threshold (>= 3).", "No pre-existing conditions disclosed.", "Customer expressed positive intent (interested)."]}`

> 🔧 **create_lead**(`{"customer_name": "Cooperative Test Customer", "phone": "9000000001", "city": "Bangalore", "age": 34, "family_size": 4, "conditions": null, "budget": 2000, "intent": "interested", "qualification": "hot", "qualification_reasons": [], "objections_raised": [], "call_summary": "Cooperative customer, all qualification questions answered directly, family of 4 with no current cover \u2014 good floater fit.", "next_action": "send_quote"}`) → `{"lead_id": "lead_ee9eb6b0a40b", "created_at": "2026-09-30T11:19:35.272397+00:00"}`

**Assistant:** Thank you, that's really helpful. Based on what you've told me, I'd like to arrange a quote for a family floater plan — would that work?

**Customer:** Yes, please.

**Assistant:** Wonderful, I'll have that sent over. Thanks so much for your time today!
