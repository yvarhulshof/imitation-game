<script lang="ts">
	import Lobby from '$lib/components/Lobby.svelte';
	import Game from '$lib/components/Game.svelte';
	import { currentRoom, gameState, messages } from '$lib/stores/game';
	import { socket } from '$lib/stores/socket';
	import type { GameState, ChatMessage } from '$lib/stores/game';

	$effect(() => {
		const s = $socket;
		if (!s) return;

		s.on('room_joined', (data: { game: GameState }) => {
			gameState.set(data.game);
			currentRoom.set(data.game.room_id);
			messages.set([]);
		});

		s.on('player_joined', (data: { player_id: string; player_name: string }) => {
			gameState.update((state) => {
				if (!state) return state;
				return {
					...state,
					players: [
						...state.players,
						{
							id: data.player_id,
							name: data.player_name,
							player_type: 'human',
							is_alive: true,
							is_host: false
						}
					]
				};
			});
		});

		s.on('player_left', (data: { player_id: string; player_name: string }) => {
			gameState.update((state) => {
				if (!state) return state;
				return {
					...state,
					players: state.players.filter((p) => p.id !== data.player_id)
				};
			});
		});

		s.on('host_changed', (data: { new_host_id: string }) => {
			gameState.update((state) => {
				if (!state) return state;
				return {
					...state,
					players: state.players.map((p) => ({
						...p,
						is_host: p.id === data.new_host_id
					}))
				};
			});
		});

		s.on('new_message', (message: ChatMessage) => {
			messages.update((msgs) => [...msgs, message]);
		});

		s.on('error', (data: { message: string }) => {
			console.error('Socket error:', data.message);
		});

		return () => {
			s.off('room_joined');
			s.off('player_joined');
			s.off('player_left');
			s.off('host_changed');
			s.off('new_message');
			s.off('error');
		};
	});
</script>

<svelte:head>
	<title>Imitation Game</title>
</svelte:head>

{#if $currentRoom}
	<Game />
{:else}
	<Lobby />
{/if}
