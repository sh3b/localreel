// The three destinations. `key` is the keyboard shortcut and the number shown
// in the top bar.
export const NAV = [
	{ href: '/', label: 'feed', key: '1' },
	{ href: '/library', label: 'library', key: '2' },
	{ href: '/add', label: 'add', key: '3' }
] as const;

export function isActive(href: string, pathname: string): boolean {
	return href === '/' ? pathname === '/' : pathname.startsWith(href);
}
