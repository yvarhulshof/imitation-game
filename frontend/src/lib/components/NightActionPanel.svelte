<script lang="ts">
	import { gameState, myRole, werewolfVoteCounts, myNightAction, werewolfIds, currentRoom } from '$lib/stores/game';
	import { socket } from '$lib/stores/socket';

	const roleActionText: Record<string, { title: string; description: string }> = {
		werewolf: { title: 'Choose Your Prey', description: 'Vote to kill a villager' },
		seer: { title: 'Investigate', description: 'Choose someone to reveal their role' },
		doctor: { title: 'Protect', description: 'Choose someone to save tonight' },
		villager: { title: 'Night Falls', description: 'Wait for dawn...' }
	};

	let myPlayer = $derived($gameState?.players.find((p) => p.id === $socket?.id));

	// Get valid targets based on role
	let validTargets = $derived.by(() => {
		if (!$gameState || !myPlayer?.is_alive) return [];

		const alivePlayers = $gameState.players.filter((p) => p.is_alive);

		if ($myRole === 'werewolf') {
			// Werewolves can't target other werewolves
			return alivePlayers.filter((p) => !$werewolfIds.includes(p.id));
		} else if ($myRole === 'seer') {
			// Seer can investigate anyone except self
			return alivePlayers.filter((p) => p.id !== $socket?.id);
		} else if ($myRole === 'doctor') {
			// Doctor can protect anyone including self
			return alivePlayers;
		}

		return [];
	});

	function submitAction(targetId: string) {
		if (!$currentRoom || !myPlayer?.is_alive) return;

		$socket?.emit('night_action', { target_id: targetId });
		myNightAction.set(targetId);
	}

	let actionInfo = $derived(roleActionText[$myRole ?? 'villager']);
</script>

<div class="night-panel" class:werewolf={$myRole === 'werewolf'}>
	<h3>{actionInfo.title}</h3>
	<p class="description">{actionInfo.description}</p>

	{#if !myPlayer?.is_alive}
		<p class="dead-notice">You are dead. Watch from the shadows...</p>
	{:else if $myRole === 'villager'}
		<p class="waiting">The night is dark and full of terrors...</p>
	{:else}
		<ul class="target-list">
			{#each validTargets as target (target.id)}
				<li>
					<button
						class="target-btn"
						class:selected={$myNightAction === target.id}
						onclick={() => submitAction(target.id)}
					>
						<span class="player-name">{target.name}</span>
						{#if $myRole === 'werewolf' && $werewolfVoteCounts[target.id]}
							<span class="vote-count">
								{$werewolfVoteCounts[target.id]} vote{$werewolfVoteCounts[target.id] > 1 ? 's' : ''}
							</span>
						{/if}
					</button>
				</li>
			{/each}
		</ul>

		{#if $myNightAction}
			<p class="action-status">
				Target selected: {validTargets.find((p) => p.id === $myNightAction)?.name ?? 'Unknown'}
			</p>
		{/if}
	{/if}
</div>

<style>
	.night-panel {
		background-color: var(--bg-tertiary);
		padding: 1rem;
		border-radius: 8px;
		margin-bottom: 1rem;
		border-left: 4px solid #6c5ce7;
	}

	.night-panel.werewolf {
		border-left-color: #dc3545;
	}

	h3 {
		margin: 0 0 0.5rem 0;
		color: var(--text-primary);
	}

	.description {
		font-size: 0.9rem;
		color: var(--text-secondary);
		margin: 0 0 1rem 0;
	}

	.target-list {
		list-style: none;
		padding: 0;
		margin: 0;
	}

	.target-btn {
		width: 100%;
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.75rem 1rem;
		background-color: var(--bg-secondary);
		border: 2px solid transparent;
		border-radius: 4px;
		cursor: pointer;
		color: var(--text-primary);
		margin-bottom: 0.5rem;
		transition: all 0.2s ease;
	}

	.target-btn:hover {
		background-color: var(--bg-primary);
		border-color: #6c5ce7;
	}

	.werewolf .target-btn:hover {
		border-color: #dc3545;
	}

	.target-btn.selected {
		border-color: #6c5ce7;
		background-color: rgba(108, 92, 231, 0.1);
	}

	.werewolf .target-btn.selected {
		border-color: #dc3545;
		background-color: rgba(220, 53, 69, 0.1);
	}

	.player-name {
		font-weight: 500;
	}

	.vote-count {
		font-size: 0.85rem;
		color: #dc3545;
		font-weight: bold;
	}

	.action-status {
		margin-top: 1rem;
		font-size: 0.9rem;
		color: var(--text-secondary);
		font-style: italic;
	}

	.dead-notice,
	.waiting {
		color: var(--text-secondary);
		font-style: italic;
	}
</style>
