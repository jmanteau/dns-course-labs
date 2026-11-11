-- Turn every external link into plain text followed by a clickable icon,
-- so the text reads the same in print and the icon alone marks the link.
function Link(link)
  if not link.target:match("^https?://") then
    return nil
  end
  local label = pandoc.utils.stringify(link.content)
  local icon = pandoc.Link({}, link.target, link.title,
    pandoc.Attr("", {"ext"}, {{"aria-label", label}}))

  -- Keep the icon on the same line as the last word, so it never wraps alone.
  local text = link.content
  local last = text[#text]
  if last and last.t == "Str" then
    text:remove(#text)
    text:insert(pandoc.Span({last, icon}, pandoc.Attr("", {"nowrap"})))
  else
    text:insert(icon)
  end
  return text
end
