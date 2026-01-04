<script lang="ts">
	import { myRole, myTeam, werewolfIds, gameState, seerResult } from '$lib/stores/game';
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
		{#if $myRole === 'seer' && $seerResult}
			<div class="seer-result">
				<span class="result-label">Investigation Result:</span>
				<span class="result-name">{$seerResult.target_name}</span> is a
				<span class="result-role" class:mafia={$seerResult.role === 'werewolf'}>
					{roleNames[$seerResult.role]}
				</span>
			</div>
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

	.seer-result {
		margin-top: 0.75rem;
		padding-top: 0.75rem;
		border-top: 1px solid var(--bg-secondary);
		font-size: 0.9rem;
	}

	.result-label {
		color: var(--text-secondary);
		display: block;
		font-size: 0.8rem;
		margin-bottom: 0.25rem;
	}

	.result-name {
		font-weight: bold;
		color: var(--text-primary);
	}

	.result-role {
		font-weight: bold;
		color: var(--accent);
	}

	.result-role.mafia {
		color: #dc3545;
	}
</style>
