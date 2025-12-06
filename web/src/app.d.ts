// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
	namespace App {
		// interface Error {}
		// interface Locals {}
		// interface PageData {}
		// interface PageState {}
		// interface Platform {}
	}

	namespace svelteHTML {
		interface HTMLAttributes<T> {
			"on:consider"?: (event: CustomEvent<any>) => void;
			"on:finalize"?: (event: CustomEvent<any>) => void;
		}
	}
}

export {};
