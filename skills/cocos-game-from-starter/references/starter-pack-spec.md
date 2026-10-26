# Design starter contract v2

Send this contract together with the complete accompanying author kit (generator scripts, shared product_contract.py and the parseable 70-level example) to Grok or another author. The kit is self-contained; never tell the author to read an unprovided local script. Write all package content in English. Do not include platform IDs, credentials, implementation code, build claims or fabricated solver results. A design starter is a planning/data input; an initial download payload is an unrelated runtime size concept.

## Files and ownership

Always provide START_HERE.md, GAME_DESIGN.md, ART_DIRECTION.md, UI_PAGES.md, ECONOMY.json, COPY_EN.md, AUDIO.md and starter.json. Level games also provide levels/README.md, levels/level_plan.json, levels/solutions.json and the actual layout file referenced by each level. Endless games have no invented level map/level_plan/solutions.

START_HERE indexes every supplied file and records what to keep/change/remove if original source is attached. GAME_DESIGN defines actual input, legal actions, state changes, win/fail, pause, restart and reward consumers, and has a section named `Built-in modules`. Supplied source, original archives and saves are preserved.

The author owns the submitted level order, layout and seed. `plan_ownership` is `import_preserve`: the receiving production tool imports the accepted table; it does not call make_level_plan again or replace designed levels with random bonus positions. The generator is a planning aid before the author finalizes layouts. A changed seed after acceptance is a design change requiring affected layout/solution validation.

## Structured decisions: starter.json

Use schema `design_starter.v2`, language `en`, mode `levels` or `endless`, plan_ownership `import_preserve`, modules including `currency`, `result_x2`, `home_gift` and, for level games, `levels`; add `skins` only when enabled. Features `ranking`, `sharing`, `ad_skip`, `cross_promotion`, `daily_checkin` are false for the ordinary starter. Explicit non-social project extensions are separate project decisions.

`home_layout` is `{"middle_left_min":1,"middle_right_min":1,"below_play_max":5,"button_scale":2}`. `energy_enabled` is a boolean; if true, `rewarded_energy_amount` is exactly 3. Supply `pages` as objects with unique `id` and `buttons` with explicit `action`. No ranking/share/invite/skip routes. No Credits or equivalent About/production-explanation pages; retain license and source records in project documentation. See the complete parseable example in ../examples/minimal-starter/.

## Level and reward data

New default level games have at least 70 total slots. The total already includes normal, bonus and milestone levels; no extra levels are silently inserted at intake. Milestones are exactly 10,20,30,… up to the largest multiple of ten within the total. An incomplete final chapter adds no milestone and no extra limited skin. Thus 75 levels have milestones 10..70, not 75.

Each complete ten-level chapter contains one easy bonus slot. It is chosen once from the saved integer `seed`, excluding levels 1..3, chapter starts, the milestone and its immediate predecessor. A short tail has no new bonus requirement. Keep positions and actual layouts in the submitted table. The example includes the deterministic result so an author without the production scripts can see the entire format.

Plan fields: schema `level_plan.v1`, mode `levels`, meaningful `why`, `currency`, `coins_per_level`, total_levels, milestone_every=10, seed, reward_seed, reward_policy=`seeded_band.v1`, milestone_policy=`multiples_only.v1`, limited_skin_mode=`final` or `every_10`, bonus_multiplier=3, and ordered `levels`. Each row has level, type, positive difficulty, coins, layout_file and layout_sha256. New mechanics carry tags `["intro"]`.

Normal and milestone rewards are generated once by reward_seed: coins=coins_base+coins_roll, coins_band=max(1,round(coins_base*0.10)), abs(coins_roll)<=coins_band. Keep at least two distinct values per complete chapter and five across 70 levels. Retry reads stored coins; it never rerolls. Bonus coins are exactly three times the ceiling of that chapter's median normal-level coins; x2 settlement yields six times that reference. A coin milestone's extra first-clear amount equals the sum of the previous five stored rewards. Skin milestones reference the matching limited skin ID. Difficulty rises across non-bonus levels; bonus is an intentional easy exception.

Each actual layout has a SHA-256 and a proposed solution bound to those bytes. solutions.json contains `levels`, each with level, layout_sha256, solvable=true and a nonempty `actions` array. The receiver must independently replay solutions with the real game's rules; a supplied solvable flag or this validator cannot prove solvability.

## Economy and skins

ECONOMY.json has themed currency, positive integer coins_per_level, boolean skin_module and arrays skins/backgrounds. Disabled skins means both arrays empty. Names, IDs and art directions must be complete; production copies names/art by ID into the accepted table, never by unstable list position.

`final`: one limited skin, awarded at the last actual milestone, then one free, seven common, six rare, three epic and two legendary = 20 hero skins. `every_10`: one distinct limited skin for each milestone, all first, followed by the same 19 nonlimited skins. Total = 19+floor(total_levels/10): 70 and 75 levels both have 26 skins/7 limited; 85 levels have 27/8. Every limited skin has its award level and matching level-plan reward ID.

Backgrounds are [] when no scene can be dressed; otherwise ten entries ordered free, three common, three rare, two epic, one legendary. Ordinary purchasable skins/backgrounds use currency only. Level-limited skins are earned at their milestone; the documented endless limited route remains its existing separate coin/ad rule. No ranking or check-in skins. Numeric prices/bonuses use the common skin generator and audit, not a second pricing model in this design package.

## Pages, art, audio and advertising

UI_PAGES lists each actual page/modal and every button's English text/icon, approximate position, size and resulting action, including free Retry/Home/Next, settings return ownership, last-level destination, pause and ad cancellation. Home has a prominent title/character, functional icons in both middle side regions and at most five below PLAY. Buttons use visible dimensions twice the original reference when one exists; without an original, production records the design baseline. Do not force all icons into bottom rows. Gameplay keeps the core play area at least 80% of the screen; persistent controls stay outside its essential interaction area.

ART_DIRECTION describes bright cute art, calm composed backgrounds, coherent generated title/logo and button-with-text images, themed currency icons, bitmap digits, safe panel interiors and no distorted lettering/dark text backplates. Production art rules and runtime bounds are checked in the art stage. AUDIO specifies moods and required music/effects from licensed sources, never synthetic placeholder claims.

Every applicable settlement offers rewarded x2; home gift is a separate currency offer; bonus settlement doubles the stored 3x amount to 6x. Revive continues the same challenge, trial skins last one level. Energy-enabled games offer +3 energy. Every offer retains a free exit; cancellation/failure grants nothing and restores play. No ad skip, ranking, sharing, cross promotion or platform secrets.

## Intake validation and limits

Run scripts/validate_starter.py --input <directory-or-ZIP> --out <new-report.json> before production. It checks required files, data fields/counts/order, SHA references, seed arithmetic, structured feature/routes and obvious language/credential violations. It does not judge English quality, originality, actual gameplay, art, or execute supplied scripts/solutions. inspect_starter.py remains a safe inventory tool; exit 0 there is not acceptance.

The checked-in minimal-starter is a deliberately simple 70-level corridor fixture illustrating all fields. It is not a polished game or a claim that 70 trivial layouts constitute production content. Real game layouts and real solution replay remain required. Workshop v3 inputs use their dedicated signed handoff contract and preserve accepted workshop data; they are not silently converted into this ordinary design template.
