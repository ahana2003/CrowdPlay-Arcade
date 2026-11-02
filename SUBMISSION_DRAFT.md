# Devpost submission draft — CrowdPlay Arcade

## One-line pitch
CrowdPlay Arcade turns Twitch chat into a shared mini-game controller: the streamer starts a round, and viewers compete with simple chat commands.

## Project description
CrowdPlay Arcade is a stream overlay with three lightweight audience games: Tic-Tac-Toe, Guess the Word, and Math Challenge. A streamer can start a random game, while viewers interact in Twitch chat using the command shown on the overlay. Tic-Tac-Toe lets two chatters join and take turns, Guess the Word lets chat reveal a hidden word, and Math Challenge rewards the first correct answer. A clickable local mode lets you play without a Twitch account. The same interface can connect to Twitch chat after you configure a private chat token.

## What is implemented
- Three chat-playable games and a shared score board.
- A browser overlay, clickable local play mode, and complete sample rounds.
- A Flask server with a health indicator, event feed, and Twitch IRC chat reader.
- Windows startup script and setup instructions.

## Important before submission
- Run the project with your own Twitch account and verify the live chat status and commands. Do not say live Twitch was tested until you have done that.
- Add your public GitHub/GitLab/Bitbucket repository URL.
- Record and upload a public YouTube demo under 3 minutes showing the project working on Twitch and how you used Codex.
- Add the Codex session ID for the thread where most project work happened. The current thread ID shown in this environment is `01a19106-9600-7f91-8888-6e2d62434bd1`; verify with `/status` before submitting.
- Make sure the participant meets the event's age eligibility and submit before the Devpost deadline.

## Suggested demo video (under 3 minutes)
1. Show the running overlay and briefly describe how it helps a streamer make chat part of the game.
2. Start Tic-Tac-Toe and play from Twitch chat using `!join` and `!move`.
3. Show one quick Guess the Word or Math Challenge round.
4. Show the relevant Codex thread and explain that Codex helped build the app and setup flow.

## Tags to consider
Twitch, chat games, stream overlay, community interaction, Flask, Python




