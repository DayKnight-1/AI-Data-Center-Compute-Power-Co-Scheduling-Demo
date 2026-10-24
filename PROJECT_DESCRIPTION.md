# Project Description

## How I Interpreted the Problem

The Track 2 prompt asked one deceptively simple question: *when green power is cheap but unreliable, and compute demand is not aligned with it, how should a data center decide what to run and when?*

I broke the problem into three parts:

1. **What varies?** Grid price, green availability, and carbon intensity all change over the day. So do compute tasks, which arrive at different times and have different urgency.
2. **What can I control?** The *scheduling decision*: which task runs in which time slot, at which compute tier, possibly split across multiple slots, and how the battery charges/discharges alongside it.
3. **What am I optimizing?** Not one number, but a trade-off: *cheaper* vs *greener* vs *on time*.

From this, I defined the goal as:

> Minimize `cost + λ · carbon + SLA penalties`, subject to power balance, capacity, and deadline constraints.

`λ` (CNY per kg of CO₂) is the **explicit dial** between "cheaper" and "greener" — I expose it as a slider so a viewer can see how the optimal schedule shifts.

## How I Approached It

I built a **full closed loop**:

**Problem generator → 4 strategies → metrics → 4 visualizations → live demo**

1. **Task model.** I modeled two task classes (`deadline` and `elastic`) with three compute tiers (`slow`, `std`, `fast`). Slowing a task down uses less power *and* less energy, but takes more wall-clock time — which is exactly the tension a scheduler can exploit.
2. **Four strategies.**
   - *Baseline*: first-come, first-served, no scheduling.
   - *Simple off-peak*: delay to hours with cheap price.
   - *Greedy*: for each task, pick the (slot, tier) combination that minimizes `Σ(price + λ·carbon)·p`.
   - *Smart scheduling* (ours): run Greedy for an initial plan, then run a **randomized local search** over three move types — tier switching, time shifting, and task splitting with a forced 2-hour gap — accepting moves that don't worsen the objective by more than 5 %.
3. **Battery integration.** Battery follows a simple threshold policy (discharge at price > 1.0, charge at < 0.4). Cycles and energy throughput are reported.
4. **Lower-bound reference.** I compute a **relaxed analytic bound** by assuming infinite capacity and letting each task independently pick its cheapest slot. The dashboard shows the gap between my solution and this bound.
5. **Robustness experiment.** On a second page, I simulate **forecast error**: schedule against a noisy predicted price, then re-evaluate against the true price. I sweep ±0/10/20/30 % error and report degradation.

## Why My Method Is Unique

Three design choices distinguish me from a generic "energy-aware scheduler":

### 1. I separate *what* from *when*.

Most demos schedule tasks to a time slot and stop there. I also choose the **compute tier** — slowing a job down when electricity is scarce (or fast-forwarding it when green power is abundant). This is a *second degree of freedom* beyond time shifting, and it matters: my local search finds solutions where `slow` tiers cluster into low-price, low-carbon hours, and `fast` tiers compress work into green-rich mid-day windows.

### 2. I model **splitting**.

Long jobs can be interrupted and resumed elsewhere with a forced gap, with an explicit per-interrupt penalty. This is how real training jobs behave (checkpoint & resume), and it lets the scheduler exploit transient price dips that whole-job shifting would miss.

### 3. I measure **gap to a limit**, not just raw savings.

Anyone can show "my method saves 30 %." I additionally show **how close I are to the best possible** given the task constraints — with an honest caveat (in the README) that my bound is relaxed, not a certificate of optimality. Reporting the gap is the single most important signal of whether a method is *good* or merely *working*.

## The "So What"

On a 24-hour horizon with realistic task loads:

- **Smart scheduling** reduces total cost by **~30–45 %** vs. the no-scheduling baseline, depending on the scenario.
- **Carbon** drops by **~25–35 %**.
- **Missed tasks** stay at 0 in normal scenarios.
- **Robustness**: even with **±30 % price forecast error**, the smart scheduler retains **most of its advantage** — because the two strongest levers (tier choice and battery) do not depend on perfect foresight.

## What I Would Do With More Time

If I had more time, I would focus on these meaningful improvements:

1. **Make the battery model more realistic.** 
Right now, my battery model is "perfect" (no energy lost when charging/discharging). I would add a simple 10% energy loss to make the simulation closer to real-world physics.

2. **Test with more "surprise" scenarios.** 
My robustness page currently only tests wrong electricity price predictions. I would also add tests for sudden cloudy weather (less solar power) or unexpected task arrivals, to see if the scheduler can still handle the chaos.

3. **Allow custom user inputs.** 
Currently, users can only choose from my 4 built-in scenarios. I would add a feature where users can upload their own daily electricity prices or create their own task lists to see how the algorithm adapts.

4. **Tweak the algorithm parameters.** 
I would experiment with different "penalty weights" (like how much to punish a missed deadline) and try running the local search for more iterations to see if I can squeeze out even more cost savings.