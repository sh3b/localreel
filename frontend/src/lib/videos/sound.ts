// Videos start muted, because browsers block autoplay with sound. Once someone
// turns the sound on, remember it for the next visit.
const SOUND_KEY = 'localreel.sound';

export function readSoundOn(): boolean {
	try {
		return localStorage.getItem(SOUND_KEY) === 'on';
	} catch {
		return false;
	}
}

export function saveSoundOn(on: boolean): void {
	try {
		localStorage.setItem(SOUND_KEY, on ? 'on' : 'off');
	} catch {
		// Storage can be refused; the choice still holds for this visit.
	}
}
