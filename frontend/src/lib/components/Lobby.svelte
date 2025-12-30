<script lang="ts">
	import { gameState, playerName, currentRoom, messages } from '$lib/stores/game';
	import { getSocket, connected } from '$lib/stores/socket';
	import type { GameState, ChatMessage } from '$lib/stores/game';

	let nameInput = $state('');
	let roomInput = $state('');
	let error = $state('');

	function createRoom() {
		if (!nameInput.trim()) {
			error = 'Please enter your name';
			return;
		}

		const socket = getSocket();
		if (!socket) return;

		playerName.set(nameInput.trim());

		socket.emit('create_room', {}, (response: { room_id: string }) => {
			currentRoom.set(response.room_id);
			socket.emit(
				'join_room',
				{
					room_id: response.room_id,
					player_name: nameInput.trim()
				},
				() => {}
			);
		});
	}

	function joinRoom() {
		if (!nameInput.trim()) {
			error = 'Please enter your name';
			return;
		}
		if (!roomInput.trim()) {
			error = 'Please enter a room code';
			return;
		}

		const socket = getSocket();
		if (!socket) return;

		playerName.set(nameInput.trim());

		socket.emit(
			'join_room',
			{
				room_id: roomInput.trim(),
				player_name: nameInput.trim()
			},
			(response: { success: boolean; error?: string }) => {
				if (!response.success) {
					error = response.error || 'Failed to join room';
				}
			}
		);
	}

	$effect(() => {
		const socket = getSocket();
		if (!socket) return;

		socket.on('room_joined', (data: { game: GameState }) => {
			gameState.set(data.game);
			currentRoom.set(data.game.room_id);
			messages.set([]);
		});

		socket.on('player_joined', (data: { player_id: string; player_name: string }) => {
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

		socket.on('new_message', (message: ChatMessage) => {
			messages.update((msgs) => [...msgs, message]);
		});

		socket.on('error', (data: { message: string }) => {
			error = data.message;
		});

		return () => {
			socket.off('room_joined');
			socket.off('player_joined');
			socket.off('new_message');
			socket.off('error');
		};
	});
</script>

<div class="lobby">
	<h1>Imitation Game</h1>
	<p class="subtitle">A social deduction game with AI players</p>

	{#if !$connected}
		<p class="connecting">Connecting to server...</p>
	{:else}
		<div class="form">
			<input type="text" bind:value={nameInput} placeholder="Your name" />

			<div class="buttons">
				<button onclick={createRoom}>Create Room</button>
				<span class="or">or</span>
				<div class="join-group">
					<input type="text" bind:value={roomInput} placeholder="Room code" />
					<button onclick={joinRoom}>Join</button>
				</div>
			</div>

			{#if error}
				<p class="error">{error}</p>
			{/if}
		</div>
	{/if}
</div>

<style>
	.lobby {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 100vh;
		padding: 2rem;
	}

	h1 {
		font-size: 3rem;
		color: var(--accent);
		margin-bottom: 0.5rem;
	}

	.subtitle {
		color: var(--text-secondary);
		margin-bottom: 2rem;
	}

	.connecting {
		color: var(--text-secondary);
	}

	.form {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		width: 100%;
		max-width: 400px;
	}

	.buttons {
		display: flex;
		align-items: center;
		gap: 1rem;
		flex-wrap: wrap;
	}

	.or {
		color: var(--text-secondary);
	}

	.join-group {
		display: flex;
		gap: 0.5rem;
		flex: 1;
	}

	.join-group input {
		flex: 1;
		min-width: 100px;
	}

	.error {
		color: var(--accent);
		font-size: 0.9rem;
	}
</style>
