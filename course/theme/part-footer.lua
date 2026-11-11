-- Add a footer naming the current part ("PART 1 · DNS OVERVIEW") to every slide.
-- The part changes at each chapter divider (a level-2 heading with class "divider").
-- Dividers and the closing xkcd slide get no footer.
function Pandoc(doc)
  local part = doc.meta["footer-title"] and pandoc.utils.stringify(doc.meta["footer-title"]) or "DNS Fundamentals"
  local count = 0
  local blocks = pandoc.List()

  for _, block in ipairs(doc.blocks) do
    blocks:insert(block)
    if block.t == "Header" and block.level == 2 then
      if block.classes:includes("divider") then
        count = count + 1
        part = "Part " .. count .. " · " .. pandoc.utils.stringify(block.content)
      elseif not block.classes:includes("xkcd") then
        blocks:insert(pandoc.RawBlock("html", '<div class="part-footer">' .. part .. '</div>'))
      end
    end
  end

  doc.blocks = blocks
  return doc
end
