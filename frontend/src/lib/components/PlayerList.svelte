<script lang="ts">
	import { gameState } from '$lib/stores/game';
</script>

<div class="player-list">
	<h3>Players</h3>
	{#if $gameState}
		<ul>
			{#each $gameState.players as player (player.id)}
				<li class:host={player.is_host} class:dead={!player.is_alive}>
					{player.name}
					{#if player.is_host}<span class="badge">Host</span>{/if}
				</li>
			{/each}
		</ul>
	{:else}
		<p class="empty">No players yet</p>
	{/if}
</div>

<style>
	.player-list {
		background-color: var(--bg-secondary);
		padding: 1rem;
		border-radius: 8px;
	}

	h3 {
		margin-bottom: 1rem;
		color: var(--text-primary);
	}

	ul {
		list-style: none;
	}

	li {
		padding: 0.5rem 0;
		border-bottom: 1px solid var(--bg-tertiary);
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	li:last-child {
		border-bottom: none;
	}

	li.dead {
		opacity: 0.5;
		text-decoration: line-through;
	}

	.badge {
		font-size: 0.75rem;
		background-color: var(--accent);
		padding: 0.1rem 0.4rem;
		border-radius: 4px;
	}

	.empty {
		color: var(--text-secondary);
		font-style: italic;
	}
</style>
