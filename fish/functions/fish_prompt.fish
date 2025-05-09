function fish_prompt
    set -l colors red green yellow blue magenta cyan
    set -l color_count (count $colors)

    set_color cyan
    echo -n (whoami)' '

    set -l path_components (string split / (prompt_pwd))

    for i in (seq (count $path_components))
        set -l dir $path_components[$i]
        if test -n "$dir"
            set -l color $colors[(math "($i - 1) % $color_count + 1")]
            set_color $color
            echo -n "/$dir"
        end
    end

    set_color normal
    echo -n ' > '
end
