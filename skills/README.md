# Football Match Coach skill

This portable ChatGPT skill turns football match statistics, event notes, or scoresheets you provide into a balanced coaching analysis. It has no server component and does not require ClubATX credentials. It analyzes only information provided in the conversation or through tools available in your ChatGPT workspace.

**Public source:** [Football Match Coach on GitHub](https://github.com/g-six/clubatx-ai/tree/codex/public-football-match-coach/skills/football-match-coach). [Download the ready-to-upload ZIP](https://github.com/g-six/clubatx-ai/raw/refs/heads/codex/public-football-match-coach/skills/football-match-coach.zip).

## Install in ChatGPT

1. Download the ready-to-upload ZIP using the link above.
2. In ChatGPT, open **Plugins** → **Skills** → **Create** → **Upload from your computer**.
3. Select the ZIP and complete ChatGPT's upload scan.
4. Start a chat and provide a completed match's score and statistics, event notes, or scoresheet. Ask for a team-focused report and identify the team if it is not clear.

The ChatGPT Skills feature is currently available to eligible Business, Enterprise, Healthcare, and Edu accounts, subject to workspace settings and product availability. A workspace administrator may need to enable skill use and uploads. See [Skills in ChatGPT](https://help.openai.com/en/articles/20001066-skills-in-chatgpt) for current availability and sharing options. The source is publicly available on GitHub, but uploading it does not publish it to a universal ChatGPT directory; a workspace can share an installed skill with its members using its own sharing controls.

## Build the ZIP locally

From the `skills/` directory:

```sh
zip -r football-match-coach.zip football-match-coach
```

The upload ZIP should contain the skill folder at its root, with `SKILL.md` inside. The packaged source is [`football-match-coach/SKILL.md`](./football-match-coach/SKILL.md).
