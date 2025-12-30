import { io, Socket } from 'socket.io-client';
import { writable } from 'svelte/store';

const SOCKET_URL = 'http://localhost:8000';

export const socket = writable<Socket | null>(null);
export const connected = writable(false);

export function initSocket(): Socket {
	const newSocket = io(SOCKET_URL, {
		transports: ['websocket']
	});

	newSocket.on('connect', () => {
		connected.set(true);
		console.log('Connected to server');
	});

	newSocket.on('disconnect', () => {
		connected.set(false);
		console.log('Disconnected from server');
	});

	socket.set(newSocket);
	return newSocket;
}

export function getSocket(): Socket | null {
	let s: Socket | null = null;
	socket.subscribe((value) => (s = value))();
	return s;
}
