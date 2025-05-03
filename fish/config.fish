set -g fish_greeting ""


if not status --is-interactive
	set -g interactive_mode = false
end
