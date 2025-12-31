import { writable } from 'svelte/store';

export interface Player {
	id: string;
	name: string;
	player_type: 'human' | 'ai';
	is_alive: boolean;
	is_host: boolean;
}

export interface ChatMessage {
	player_id: string;
	player_name: string;
	content: string;
	timestamp: number;
}

export interface GameState {
	room_id: string;
	phase: 'lobby' | 'day' | 'night' | 'voting' | 'ended';
	players: Player[];
	round_number: number;
	phase_ends_at: number | null;
	phase_duration: number;
}

export const gameState = writable<GameState | null>(null);
export const messages = writable<ChatMessage[]>([]);
export const playerName = writable<string>('');
export const currentRoom = writable<string | null>(null);
export const phaseEndsAt = writable<number | null>(null);
export const phaseDuration = writable<number>(0);
