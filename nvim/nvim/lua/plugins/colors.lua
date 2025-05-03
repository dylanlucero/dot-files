return {
  {
    "gruvbox-community/gruvbox",  -- Gruvbox colorscheme
    lazy = false,                 -- Load immediately when Neovim starts
    priority = 1000,              -- Ensure it loads before other plugins
    config = function()
      vim.cmd("colorscheme gruvbox")  -- Set colorscheme to gruvbox
      vim.o.background = "dark"  -- You can change to "light" if you prefer
    end
  }
}

