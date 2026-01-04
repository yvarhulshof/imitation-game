<script lang="ts">
	import { nightDeaths, gameState } from '$lib/stores/game';

	const roleNames: Record<string, string> = {
		villager: 'Villager',
		werewolf: 'Werewolf',
		seer: 'Seer',
		doctor: 'Doctor'
	};

	let visible = $state(false);

	$effect(() => {
		// Show announcement when transitioning to DAY and there are deaths to report
		// or when night_result event is received
		if ($nightDeaths.length >= 0 && $gameState?.phase === 'day') {
			visible = true;
			// Auto-hide after 5 seconds
			const timer = setTimeout(() => {
				visible = false;
			}, 5000);
			return () => clearTimeout(timer);
		}
	});

	// Reset when leaving day phase
	$effect(() => {
		if ($gameState?.phase !== 'day') {
			visible = false;
		}
	});

	function dismiss() {
		visible = false;
	}
</script>

{#if visible && $gameState?.phase === 'day' && $gameState?.round_number > 1}
	<div class="announcement" class:peaceful={$nightDeaths.length === 0}>
		<button class="dismiss" onclick={dismiss}>&times;</button>
		{#if $nightDeaths.length === 0}
			<h3>A Peaceful Night</h3>
			<p class="reason">No one died during the night.</p>
		{:else}
			<h3>Dawn Reveals...</h3>
			{#each $nightDeaths as death (death.id)}
				<div class="death">
					<p class="name">{death.name}</p>
					<p class="role">
						was killed. They were a <span class:mafia={death.role === 'werewolf'}>
							{roleNames[death.role ?? 'villager']}
						</span>
					</p>
				</div>
			{/each}
		{/if}
	</div>
{/if}

<style>
	.announcement {
		position: fixed;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		background-color: var(--bg-secondary);
		border: 2px solid #dc3545;
		border-radius: 12px;
		padding: 2rem;
		text-align: center;
		z-index: 100;
		min-width: 300px;
		box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
		animation: fadeIn 0.3s ease-out;
	}

	.announcement.peaceful {
		border-color: var(--accent);
	}

	@keyframes fadeIn {
		from {
			opacity: 0;
			transform: translate(-50%, -50%) scale(0.9);
		}
		to {
			opacity: 1;
			transform: translate(-50%, -50%) scale(1);
		}
	}

	.dismiss {
		position: absolute;
		top: 0.5rem;
		right: 0.75rem;
		background: none;
		border: none;
		color: var(--text-secondary);
		font-size: 1.5rem;
		cursor: pointer;
		padding: 0;
		line-height: 1;
	}

	.dismiss:hover {
		color: var(--text-primary);
	}

	h3 {
		margin: 0 0 1rem 0;
		color: var(--text-primary);
		font-size: 1.5rem;
	}

	.death {
		margin-bottom: 1rem;
	}

	.death:last-child {
		margin-bottom: 0;
	}

	.name {
		font-size: 1.25rem;
		font-weight: bold;
		color: #dc3545;
		margin: 0 0 0.25rem 0;
	}

	.role {
		color: var(--text-secondary);
		margin: 0;
	}

	.role span {
		font-weight: bold;
		color: var(--accent);
	}

	.role span.mafia {
		color: #dc3545;
	}

	.reason {
		color: var(--text-secondary);
		font-style: italic;
		margin: 0;
	}
</style>
