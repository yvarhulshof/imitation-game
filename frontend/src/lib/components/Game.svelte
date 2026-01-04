<script lang="ts">
	import Chat from './Chat.svelte';
	import PlayerList from './PlayerList.svelte';
	import PhaseTimer from './PhaseTimer.svelte';
	import RoleDisplay from './RoleDisplay.svelte';
	import VotingPanel from './VotingPanel.svelte';
	import NightActionPanel from './NightActionPanel.svelte';
	import EliminationAnnouncement from './EliminationAnnouncement.svelte';
	import NightResultAnnouncement from './NightResultAnnouncement.svelte';
	import GameEndScreen from './GameEndScreen.svelte';
	import { gameState, currentRoom, gameEndData } from '$lib/stores/game';
	import { socket } from '$lib/stores/socket';

	let myPlayer = $derived($gameState?.players.find((p) => p.id === $socket?.id));
	let isHost = $derived(myPlayer?.is_host ?? false);
	let isAlive = $derived(myPlayer?.is_alive ?? true);
	let isSpectating = $derived(!isAlive && $gameState?.phase !== 'lobby' && $gameState?.phase !== 'ended');

	function startGame() {
		$socket?.emit('start_game');
	}

	function skipToVoting() {
		$socket?.emit('skip_to_voting');
	}

	function addAIPlayer() {
		$socket?.emit('add_ai_player');
	}
</script>

<EliminationAnnouncement />
<NightResultAnnouncement />
{#if $gameEndData}
	<GameEndScreen />
{/if}

<div class="game-container">
	<header>
		<h1>Imitation Game</h1>
		{#if $currentRoom}
			<span class="room-code">Room: {$currentRoom}</span>
		{/if}
		{#if $gameState}
			<span class="phase">
				{$gameState.phase}
				{#if $gameState.phase !== 'lobby' && $gameState.phase !== 'ended'}
					(Round {$gameState.round_number})
				{/if}
			</span>
			<PhaseTimer />
		{/if}
		{#if isSpectating}
			<span class="spectator-badge">Spectating</span>
		{/if}
		<div class="header-actions">
			{#if isHost && $gameState?.phase === 'lobby'}
				<button class="add-ai-btn" onclick={addAIPlayer}>+ Add AI</button>
				<button class="start-btn" onclick={startGame}>Start Game</button>
			{/if}
			{#if isHost && $gameState?.phase === 'day'}
				<button class="skip-btn" onclick={skipToVoting}>Skip to Voting</button>
			{/if}
		</div>
	</header>

	<main>
		<aside>
			<RoleDisplay />
			{#if $gameState?.phase === 'voting'}
				<VotingPanel />
			{/if}
			{#if $gameState?.phase === 'night'}
				<NightActionPanel />
			{/if}
			<PlayerList />
		</aside>

		<section class="chat-section">
			<Chat />
		</section>
	</main>
</div>

<style>
	.game-container {
		display: flex;
		flex-direction: column;
		height: 100vh;
	}

	header {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 1rem;
		background-color: var(--bg-secondary);
		border-bottom: 1px solid var(--bg-tertiary);
	}

	header h1 {
		font-size: 1.5rem;
		color: var(--accent);
	}

	.room-code {
		color: var(--text-secondary);
		font-size: 0.9rem;
	}

	.phase {
		text-transform: uppercase;
		font-size: 0.9rem;
		background-color: var(--bg-tertiary);
		padding: 0.25rem 0.75rem;
		border-radius: 4px;
	}

	.header-actions {
		margin-left: auto;
		display: flex;
		gap: 0.5rem;
	}

	.start-btn {
		background-color: var(--accent);
		color: var(--bg-primary);
		border: none;
		padding: 0.5rem 1rem;
		border-radius: 4px;
		cursor: pointer;
		font-weight: bold;
	}

	.start-btn:hover {
		opacity: 0.9;
	}

	.skip-btn {
		background-color: var(--bg-tertiary);
		color: var(--text-primary);
		border: 1px solid var(--text-secondary);
		padding: 0.5rem 1rem;
		border-radius: 4px;
		cursor: pointer;
	}

	.skip-btn:hover {
		background-color: var(--bg-secondary);
	}

	.add-ai-btn {
		background-color: var(--bg-tertiary);
		color: var(--text-primary);
		border: 1px solid var(--accent);
		padding: 0.5rem 1rem;
		border-radius: 4px;
		cursor: pointer;
	}

	.add-ai-btn:hover {
		background-color: var(--bg-secondary);
	}

	.spectator-badge {
		background-color: #64748b;
		color: white;
		padding: 0.25rem 0.75rem;
		border-radius: 4px;
		font-size: 0.85rem;
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	main {
		display: flex;
		flex: 1;
		overflow: hidden;
	}

	aside {
		width: 250px;
		padding: 1rem;
		border-right: 1px solid var(--bg-tertiary);
	}

	.chat-section {
		flex: 1;
		padding: 1rem;
		display: flex;
		flex-direction: column;
	}
</style>
