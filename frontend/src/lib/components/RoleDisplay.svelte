<script lang="ts">
	import { myRole, myTeam, werewolfIds, gameState } from '$lib/stores/game';
	import { socket } from '$lib/stores/socket';

	const roleNames: Record<string, string> = {
		villager: 'Villager',
		werewolf: 'Werewolf',
		seer: 'Seer',
		doctor: 'Doctor'
	};

	const roleDescriptions: Record<string, string> = {
		villager: 'Find and eliminate the werewolves',
		werewolf: 'Eliminate the villagers without being caught',
		seer: 'Each night, learn one player\'s role',
		doctor: 'Each night, protect one player from death'
	};

	let fellowWerewolves = $derived(
		$myRole === 'werewolf'
			? $gameState?.players
					.filter((p) => $werewolfIds.includes(p.id) && p.id !== $socket?.id)
					.map((p) => p.name) ?? []
			: []
	);
</script>

{#if $myRole}
	<div class="role-display" class:mafia={$myTeam === 'mafia'}>
		<div class="role-header">
			<span class="role-label">Your Role</span>
			<span class="role-name">{roleNames[$myRole]}</span>
		</div>
		<p class="role-description">{roleDescriptions[$myRole]}</p>
		{#if $myRole === 'werewolf' && fellowWerewolves.length > 0}
			<p class="fellow-wolves">
				Fellow werewolves: {fellowWerewolves.join(', ')}
			</p>
		{/if}
	</div>
{/if}

<style>
	.role-display {
		background-color: var(--bg-tertiary);
		border-radius: 8px;
		padding: 1rem;
		margin-bottom: 1rem;
		border-left: 4px solid var(--accent);
	}

	.role-display.mafia {
		border-left-color: #dc3545;
	}

	.role-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.5rem;
	}

	.role-label {
		font-size: 0.8rem;
		color: var(--text-secondary);
		text-transform: uppercase;
	}

	.role-name {
		font-size: 1.2rem;
		font-weight: bold;
		color: var(--text-primary);
	}

	.role-display.mafia .role-name {
		color: #dc3545;
	}

	.role-description {
		font-size: 0.9rem;
		color: var(--text-secondary);
		margin: 0;
	}

	.fellow-wolves {
		font-size: 0.85rem;
		color: #dc3545;
		margin: 0.5rem 0 0 0;
		font-style: italic;
	}
</style>
