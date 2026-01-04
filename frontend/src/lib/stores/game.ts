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

export type Role = 'villager' | 'werewolf' | 'seer' | 'doctor';
export type Team = 'town' | 'mafia';

export interface EliminatedPlayer {
	id: string;
	name: string;
	role: Role | null;
	team: Team | null;
}

export const gameState = writable<GameState | null>(null);
export const messages = writable<ChatMessage[]>([]);
export const playerName = writable<string>('');
export const currentRoom = writable<string | null>(null);
export const phaseEndsAt = writable<number | null>(null);
export const phaseDuration = writable<number>(0);
export const myRole = writable<Role | null>(null);
export const myTeam = writable<Team | null>(null);
export const werewolfIds = writable<string[]>([]);
export const voteCounts = writable<Record<string, number>>({});
export const myVote = writable<string | null>(null);
export const lastElimination = writable<{ eliminated: EliminatedPlayer | null; reason: string } | null>(null);

// Night action stores
export const werewolfVoteCounts = writable<Record<string, number>>({});
export const myNightAction = writable<string | null>(null);
export interface SeerResult {
	target_id: string;
	target_name: string;
	role: Role;
}
export const seerResult = writable<SeerResult | null>(null);
export interface NightDeath {
	id: string;
	name: string;
	role: Role | null;
}
export const nightDeaths = writable<NightDeath[]>([]);

// Game end stores
export interface GameEndPlayer {
	id: string;
	name: string;
	role: Role | null;
	team: Team | null;
	is_alive: boolean;
}
export interface GameEndData {
	winner: Team;
	players: GameEndPlayer[];
}
export const gameEndData = writable<GameEndData | null>(null);
