<script lang="ts">
	import { messages, currentRoom, playerName } from '$lib/stores/game';
	import { getSocket } from '$lib/stores/socket';
	import type { ChatMessage } from '$lib/stores/game';

	let messageInput = $state('');
	let chatContainer: HTMLDivElement;

	function sendMessage() {
		if (!messageInput.trim()) return;

		const socket = getSocket();
		if (socket && $currentRoom) {
			socket.emit('send_message', {
				room_id: $currentRoom,
				content: messageInput.trim()
			});
			messageInput = '';
		}
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			sendMessage();
		}
	}

	function formatTime(timestamp: number): string {
		return new Date(timestamp * 1000).toLocaleTimeString([], {
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	$effect(() => {
		if ($messages && chatContainer) {
			chatContainer.scrollTop = chatContainer.scrollHeight;
		}
	});
</script>

<div class="chat-container">
	<div class="messages" bind:this={chatContainer}>
		{#each $messages as message (message.timestamp)}
			<div class="message">
				<span class="time">{formatTime(message.timestamp)}</span>
				<span class="name">{message.player_name}:</span>
				<span class="content">{message.content}</span>
			</div>
		{/each}
	</div>

	<div class="input-area">
		<input
			type="text"
			bind:value={messageInput}
			onkeydown={handleKeydown}
			placeholder="Type a message..."
		/>
		<button onclick={sendMessage}>Send</button>
	</div>
</div>

<style>
	.chat-container {
		display: flex;
		flex-direction: column;
		height: 100%;
		background-color: var(--bg-secondary);
		border-radius: 8px;
		overflow: hidden;
	}

	.messages {
		flex: 1;
		overflow-y: auto;
		padding: 1rem;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.message {
		display: flex;
		gap: 0.5rem;
		line-height: 1.4;
	}

	.time {
		color: var(--text-secondary);
		font-size: 0.85rem;
	}

	.name {
		color: var(--accent);
		font-weight: 600;
	}

	.content {
		color: var(--text-primary);
	}

	.input-area {
		display: flex;
		gap: 0.5rem;
		padding: 1rem;
		background-color: var(--bg-tertiary);
	}

	.input-area input {
		flex: 1;
	}
</style>
