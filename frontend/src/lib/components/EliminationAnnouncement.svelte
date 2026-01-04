<script lang="ts">
	import { lastElimination } from '$lib/stores/game';

	const roleNames: Record<string, string> = {
		villager: 'Villager',
		werewolf: 'Werewolf',
		seer: 'Seer',
		doctor: 'Doctor'
	};

	let visible = $state(false);

	$effect(() => {
		if ($lastElimination) {
			visible = true;
			// Auto-hide after 5 seconds
			const timer = setTimeout(() => {
				visible = false;
			}, 5000);
			return () => clearTimeout(timer);
		}
	});

	function dismiss() {
		visible = false;
	}
</script>

{#if visible && $lastElimination}
	<div class="announcement" class:no-elimination={!$lastElimination.eliminated}>
		<button class="dismiss" onclick={dismiss}>&times;</button>
		{#if $lastElimination.eliminated}
			<h3>Player Eliminated!</h3>
			<p class="name">{$lastElimination.eliminated.name}</p>
			<p class="role">
				was a <span class:mafia={$lastElimination.eliminated.team === 'mafia'}>
					{roleNames[$lastElimination.eliminated.role ?? 'villager']}
				</span>
			</p>
		{:else}
			<h3>No Elimination</h3>
			<p class="reason">{$lastElimination.reason}</p>
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
		border: 2px solid var(--accent);
		border-radius: 12px;
		padding: 2rem;
		text-align: center;
		z-index: 100;
		min-width: 300px;
		box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
		animation: fadeIn 0.3s ease-out;
	}

	.announcement.no-elimination {
		border-color: var(--text-secondary);
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

	.name {
		font-size: 1.25rem;
		font-weight: bold;
		color: var(--accent);
		margin: 0 0 0.5rem 0;
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
