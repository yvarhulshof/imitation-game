<script lang="ts">
	import Lobby from '$lib/components/Lobby.svelte';
	import Game from '$lib/components/Game.svelte';
	import { currentRoom } from '$lib/stores/game';
</script>

<svelte:head>
	<title>Imitation Game</title>
</svelte:head>

{#if $currentRoom}
	<Game />
{:else}
	<Lobby />
{/if}
