<script lang="ts">
	import { gameEndData, myTeam, currentRoom, gameState, myRole, werewolfIds, messages, voteCounts, myVote, lastElimination, werewolfVoteCounts, myNightAction, seerResult, nightDeaths, type GameEndPlayer, type Team } from '$lib/stores/game';
	import { socket } from '$lib/stores/socket';

	const teamLabels: Record<Team, string> = {
		town: 'Town',
		mafia: 'Mafia'
	};

	const roleLabels: Record<string, string> = {
		villager: 'Villager',
		werewolf: 'Werewolf',
		seer: 'Seer',
		doctor: 'Doctor'
	};

	function getRoleLabel(role: string | null): string {
		if (!role) return 'Unknown';
		return roleLabels[role] || role;
	}

	function getTeamClass(team: Team | null): string {
		if (team === 'mafia') return 'mafia';
		return 'town';
	}

	function leaveGame() {
		if ($currentRoom && $socket) {
			$socket.emit('leave_room', { room_id: $currentRoom });
		}
		// Reset all game state
		currentRoom.set(null);
		gameState.set(null);
		gameEndData.set(null);
		myRole.set(null);
		myTeam.set(null);
		werewolfIds.set([]);
		messages.set([]);
		voteCounts.set({});
		myVote.set(null);
		lastElimination.set(null);
		werewolfVoteCounts.set({});
		myNightAction.set(null);
		seerResult.set(null);
		nightDeaths.set([]);
	}
</script>

{#if $gameEndData}
	<div class="game-end-overlay">
		<div class="game-end-modal">
			<h1 class="winner-header {getTeamClass($gameEndData.winner)}">
				{teamLabels[$gameEndData.winner]} Wins!
			</h1>

			{#if $myTeam === $gameEndData.winner}
				<p class="result-message victory">Victory! Your team won!</p>
			{:else}
				<p class="result-message defeat">Defeat. Your team lost.</p>
			{/if}

			<h2>All Players</h2>
			<div class="players-list">
				{#each $gameEndData.players as player (player.id)}
					<div class="player-card {getTeamClass(player.team)}" class:dead={!player.is_alive}>
						<span class="player-name">{player.name}</span>
						<span class="player-role">{getRoleLabel(player.role)}</span>
						<span class="player-team">({player.team})</span>
						{#if !player.is_alive}
							<span class="dead-badge">Dead</span>
						{/if}
					</div>
				{/each}
			</div>

			<button class="leave-btn" onclick={leaveGame}>Leave Game</button>
		</div>
	</div>
{/if}

<style>
	.game-end-overlay {
		position: fixed;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		background: rgba(0, 0, 0, 0.85);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
	}

	.game-end-modal {
		background: #1a1a2e;
		border-radius: 16px;
		padding: 2rem;
		max-width: 500px;
		width: 90%;
		text-align: center;
		box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
	}

	.winner-header {
		font-size: 2.5rem;
		margin-bottom: 1rem;
		text-transform: uppercase;
		letter-spacing: 2px;
	}

	.winner-header.town {
		color: #4ade80;
		text-shadow: 0 0 20px rgba(74, 222, 128, 0.5);
	}

	.winner-header.mafia {
		color: #ef4444;
		text-shadow: 0 0 20px rgba(239, 68, 68, 0.5);
	}

	.result-message {
		font-size: 1.25rem;
		margin-bottom: 2rem;
	}

	.result-message.victory {
		color: #4ade80;
	}

	.result-message.defeat {
		color: #ef4444;
	}

	h2 {
		font-size: 1.25rem;
		margin-bottom: 1rem;
		color: #94a3b8;
	}

	.players-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		margin-bottom: 2rem;
	}

	.player-card {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem 1rem;
		border-radius: 8px;
		background: rgba(255, 255, 255, 0.05);
		border-left: 4px solid;
	}

	.player-card.town {
		border-left-color: #4ade80;
	}

	.player-card.mafia {
		border-left-color: #ef4444;
	}

	.player-card.dead {
		opacity: 0.5;
	}

	.player-name {
		font-weight: 600;
		flex: 1;
		text-align: left;
	}

	.player-role {
		color: #94a3b8;
	}

	.player-team {
		color: #64748b;
		font-size: 0.875rem;
	}

	.dead-badge {
		background: #ef4444;
		color: white;
		padding: 0.125rem 0.5rem;
		border-radius: 4px;
		font-size: 0.75rem;
		text-transform: uppercase;
	}

	.leave-btn {
		margin-top: 1rem;
		padding: 0.75rem 2rem;
		font-size: 1rem;
		background: transparent;
		color: #94a3b8;
		border: 1px solid #475569;
		border-radius: 8px;
		cursor: pointer;
		transition: all 0.2s;
	}

	.leave-btn:hover {
		background: rgba(255, 255, 255, 0.05);
		border-color: #94a3b8;
		color: white;
	}
</style>
