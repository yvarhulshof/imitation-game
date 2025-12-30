<script lang="ts">
	import Chat from './Chat.svelte';
	import PlayerList from './PlayerList.svelte';
	import { gameState, currentRoom } from '$lib/stores/game';
</script>

<div class="game-container">
	<header>
		<h1>Imitation Game</h1>
		{#if $currentRoom}
			<span class="room-code">Room: {$currentRoom}</span>
		{/if}
		{#if $gameState}
			<span class="phase">{$gameState.phase}</span>
		{/if}
	</header>

	<main>
		<aside>
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
		margin-left: auto;
		text-transform: uppercase;
		font-size: 0.9rem;
		background-color: var(--bg-tertiary);
		padding: 0.25rem 0.75rem;
		border-radius: 4px;
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
