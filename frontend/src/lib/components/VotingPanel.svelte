<script lang="ts">
	import { gameState, voteCounts, myVote, currentRoom } from '$lib/stores/game';
	import { socket } from '$lib/stores/socket';

	let votablePlayers = $derived(
		$gameState?.players.filter((p) => p.is_alive && p.id !== $socket?.id) ?? []
	);

	let myPlayer = $derived($gameState?.players.find((p) => p.id === $socket?.id));

	function submitVote(targetId: string) {
		if (!$currentRoom || !myPlayer?.is_alive) return;

		$socket?.emit('submit_vote', { target_id: targetId });
		myVote.set(targetId);
	}
</script>

<div class="voting-panel">
	<h3>Vote to Eliminate</h3>

	{#if !myPlayer?.is_alive}
		<p class="dead-notice">You are dead and cannot vote.</p>
	{:else}
		<ul class="vote-list">
			{#each votablePlayers as player (player.id)}
				<li>
					<button
						class="vote-btn"
						class:selected={$myVote === player.id}
						onclick={() => submitVote(player.id)}
					>
						<span class="player-name">{player.name}</span>
						{#if $voteCounts[player.id]}
							<span class="vote-count">{$voteCounts[player.id]} vote{$voteCounts[player.id] > 1 ? 's' : ''}</span>
						{/if}
					</button>
				</li>
			{/each}
		</ul>
	{/if}

	{#if $myVote}
		<p class="vote-status">
			You voted for: {votablePlayers.find((p) => p.id === $myVote)?.name ?? 'Unknown'}
		</p>
	{/if}
</div>

<style>
	.voting-panel {
		background-color: var(--bg-secondary);
		padding: 1rem;
		border-radius: 8px;
		margin-bottom: 1rem;
		border-left: 4px solid #ffc107;
	}

	h3 {
		margin-bottom: 1rem;
		color: var(--text-primary);
	}

	.vote-list {
		list-style: none;
	}

	.vote-btn {
		width: 100%;
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.75rem 1rem;
		background-color: var(--bg-tertiary);
		border: 2px solid transparent;
		border-radius: 4px;
		cursor: pointer;
		color: var(--text-primary);
		margin-bottom: 0.5rem;
		transition: all 0.2s ease;
	}

	.vote-btn:hover {
		background-color: var(--bg-primary);
		border-color: var(--accent);
	}

	.vote-btn.selected {
		border-color: #ffc107;
		background-color: rgba(255, 193, 7, 0.1);
	}

	.player-name {
		font-weight: 500;
	}

	.vote-count {
		font-size: 0.85rem;
		color: #ffc107;
		font-weight: bold;
	}

	.vote-status {
		margin-top: 1rem;
		font-size: 0.9rem;
		color: var(--text-secondary);
		font-style: italic;
	}

	.dead-notice {
		color: var(--text-secondary);
		font-style: italic;
	}
</style>
