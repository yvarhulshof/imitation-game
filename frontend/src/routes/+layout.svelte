<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { initSocket } from '$lib/stores/socket';

	let { children } = $props();

	onMount(() => {
		initSocket();
	});
</script>

{@render children()}
