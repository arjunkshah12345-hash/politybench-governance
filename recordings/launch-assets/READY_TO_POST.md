# PolityBench — release note (formal)

**Demo:** https://politybench-demo.vercel.app  
**Repository:** https://github.com/arjunkshah12345-hash/politybench-governance  
**Benchmark contract:** https://github.com/arjunkshah12345-hash/politybench-governance/blob/main/BENCHMARK_SPEC.md  
**Overview:** https://github.com/arjunkshah12345-hash/politybench-governance/blob/main/README.md  

**Media (optional):** `politybench_demo_live.mp4` · screenshots in `screenshots/`

---

## POST — single post (copy/paste)

```
PolityBench is an open-source evaluation harness for measuring how well AI agents perform as constitutionally constrained national executives inside a longitudinal simulation.

Rather than scoring free-text answers to policy questions, PolityBench assigns each agent a synthetic country, a shared exogenous crisis trajectory, and imperfect observations. Agents select constrained policy actions over a multi-year horizon (monthly state evolution; executive decisions at a fixed interval). Performance is reported as a seven-dimensional welfare vector—economic, human development, stability, equity, resilience, legitimacy, and environment—together with procedural integrity and hard-constraint outcomes. A scalar robust score (expected utility with lower-tail risk adjustment) is published for ranking only. The system is a research simulator; high scores are not evidence that an AI should govern a real polity.

In the reported country-live run (scenario: macro_fiscal_crisis; fidelity: F0; one shared seed; LLM decision interval: four months), we evaluated ten large-language-model executives against a rule-based controller and a no-intervention baseline under identical conditions:

• composer-2.5 (Composer Union): robust score 24.2 (grade A)
• claude-sonnet-5-thinking-xhigh (Claude Concord): 24.1 (grade A)
• claude-fable-5-thinking-xhigh (Fable Commonwealth): 24.1 (grade B)
• cursor-grok-4.6-xhigh (Grok Territories): 24.0 (grade B)
• gemini-3.7-flash-high (Gemini Republic): 23.9 (grade C)
• gpt-5.6-sol-max (Sol Commonwealth): 23.7 (grade C)
• gpt-5.2 (GPT Commonwealth): 23.7 (grade C)
• rule_based (Meridian Federation): 23.7 (grade D)
• gpt-5.6-luna-high (Luna Republic): 23.6 (grade D)
• claude-opus-5-thinking-high (Opus Dominion): 23.4 (grade F)
• gpt-5.3-codex-xhigh (Codex Federation): 22.8 (grade F)
• hold_policy (Stasis Republic): 15.7 (grade F)

Under this seed, several language-model executives outperformed the rule-based controller, and all active executives substantially outperformed the no-intervention baseline. Full methodology, action-space limits, and excluded capabilities (tactical military and cyber operations; surveillance and electoral manipulation; omniscient access to latent simulator parameters) are specified in the benchmark contract.

Interactive replay of this run:
https://politybench-demo.vercel.app

Source repository and documentation:
https://github.com/arjunkshah12345-hash/politybench-governance
https://github.com/arjunkshah12345-hash/politybench-governance/blob/main/BENCHMARK_SPEC.md
https://github.com/arjunkshah12345-hash/politybench-governance/blob/main/README.md
```

---

## Shorter formal variant (if character-limited)

```
PolityBench is an open-source benchmark that evaluates AI agents as constrained national executives in a hybrid macroeconomic / agent-based simulation under partial observability and hard legal gates. It scores multi-year decisions across seven welfare dimensions; it does not score chat responses about policy.

Reported run (macro_fiscal_crisis, F0, shared seed; robust scores):
composer-2.5 24.2; sonnet-5-thinking-xhigh 24.1; fable-5-thinking-xhigh 24.1; grok-4.6-xhigh 24.0; gemini-3.7-flash-high 23.9; gpt-5.6-sol-max 23.7; gpt-5.2 23.7; rule_based 23.7; gpt-5.6-luna-high 23.6; opus-5-thinking-high 23.4; gpt-5.3-codex-xhigh 22.8; hold_policy 15.7.

Demo: https://politybench-demo.vercel.app
Repo: https://github.com/arjunkshah12345-hash/politybench-governance
Spec: https://github.com/arjunkshah12345-hash/politybench-governance/blob/main/BENCHMARK_SPEC.md
```

---

## Notes

- One seed / F0 for the launch figure; state that limitation if asked.
- simple_mpc excluded from the published board at author request.
- Results: `recordings/bench_summary_expanded.txt` (2026-09-01).
