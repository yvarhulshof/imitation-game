<script lang="ts">
	import { phaseEndsAt, gameState } from '$lib/stores/game';

	let remainingSeconds = $state(0);

	$effect(() => {
		const endsAt = $phaseEndsAt;
		if (endsAt === null) {
			remainingSeconds = 0;
			return;
		}

		const updateTimer = () => {
			const now = Date.now() / 1000;
			remainingSeconds = Math.max(0, Math.ceil(endsAt - now));
		};

		updateTimer();
		const interval = setInterval(updateTimer, 1000);

		return () => clearInterval(interval);
	});

	function formatTime(seconds: number): string {
		const mins = Math.floor(seconds / 60);
		const secs = seconds % 60;
		return `${mins}:${secs.toString().padStart(2, '0')}`;
	}
</script>

{#if $gameState && $gameState.phase !== 'lobby' && $gameState.phase !== 'ended'}
	<div class="timer">
		<span class="time">{formatTime(remainingSeconds)}</span>
	</div>
{/if}

<style>
	.timer {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		background-color: var(--bg-tertiary);
		padding: 0.25rem 0.75rem;
		border-radius: 4px;
	}

	.time {
		font-family: monospace;
		font-size: 1.1rem;
		font-weight: bold;
	}
</style>
