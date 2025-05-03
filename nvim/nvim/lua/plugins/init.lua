return {
  -- Telescope plugin
  {
    "nvim-telescope/telescope.nvim",
    tag = "0.1.4",                   -- Set the tag for stable version
    dependencies = { "nvim-lua/plenary.nvim" }  -- Plenary is required for Telescope
  },
  -- Mason
  {"williamboman/mason.nvim"},
}


