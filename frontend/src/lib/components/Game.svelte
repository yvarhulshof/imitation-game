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

	// Track AI count from game state
	let currentAICount = $derived($gameState?.players.filter((p) => p.player_type === 'ai').length ?? 0);
	let isInitialized = $state(false);

	// Initialize AI count when joining lobby
	$effect(() => {
		if ($gameState?.phase === 'lobby' && isHost && !isInitialized && currentAICount === 0) {
			isInitialized = true;
			// Set AI count to default on first load
			$socket?.emit('set_ai_count', { count: 6 });
		}
	});

	function startGame() {
		$socket?.emit('start_game');
	}

	function skipToVoting() {
		$socket?.emit('skip_to_voting');
	}

	function handleAICountChange(event: Event) {
		const target = event.target as HTMLInputElement;
		const newCount = parseInt(target.value);
		if (!isNaN(newCount) && newCount >= 0 && newCount <= 20) {
			$socket?.emit('set_ai_count', { count: newCount });
		}
	}
</script>

<EliminationAnnouncement />
<NightResultAnnouncement />
{#if $gameEndData}
	<GameEndScreen />
{/if}

<svelte:window on:keydown|preventDefault={(e) => e.key === 'Enter' && startGame()}/>

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
				<div class="ai-controls">
					<label for="ai-count">AI Players:</label>
					<input
						id="ai-count"
						type="number"
						value={currentAICount}
						oninput={handleAICountChange}
						min="0"
						max="20"
						class="ai-count-input"
					/>
				</div>
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
		align-items: center;
	}

	.ai-controls {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.ai-controls label {
		color: var(--text-secondary);
		font-size: 0.9rem;
	}

	.ai-count-input {
		width: 70px;
		padding: 0.5rem;
		border: 1px solid var(--text-secondary);
		border-radius: 4px;
		background-color: var(--bg-secondary);
		color: var(--text-primary);
		font-size: 0.9rem;
		text-align: center;
	}

	.ai-count-input:focus {
		outline: 2px solid var(--accent);
		outline-offset: 1px;
		border-color: var(--accent);
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
