# Sustainable Tourism Assistant for European Cities! 🌍✨

I'm here to help you discover eco-friendly travel destinations tailored to your preferences.
> **🏙️ City trips only (for now)**
> Please ask only about city trips where I can recommend you cities to visit.
Right now, I specialize in city destinations only within Europe.
---
### 📝 How it works:

1. **Share your travel preferences** → Tell me what you're looking for
2. **Answer clarifying questions** → I'll ask targeted questions to understand your needs. 
3. **Get personalized recommendations** → Receive curated suggestions based on your answers
4. **Provide feedback** → Help us improve by rating your experience

> 💡 *Please be patient—analysis may take a few minutes to ensure quality recommendations.

---
**Confused on how to start? Here are some examples of user queries to help give you an idea!**

- _"Suggest some less-known, budget-friendly European cities with parks, historical sites, or unique attractions."_
- _"Looking for a less-touristy, budget-friendly Eastern European city with interesting historical sites and local experiences.  Good coffee or unique cafes a plus!"_
- _"Cheap European city break in February."_ 

Your queries can be as vague or specific as you want! Our system will handle the rest 😉

---

### ℹ️ About this deployment

This app runs on **Hugging Face Spaces**. The original backend (Google Cloud Run + Chainlit 2.3.0) was taken offline after a security vulnerability in Chainlit 2.3.0 compromised stored credentials. This version uses Chainlit 2.11.1 (patched) and no longer stores any API credentials server-side.

As a result, the **Gemini profile now uses a Bring Your Own Key (BYOK) policy** — you paste your own [Google AI Studio API key](https://aistudio.google.com/apikey) at the start of a session. The key is kept only in session memory and is never logged or stored. The **Gemma (Free) profile** requires no key at all.
