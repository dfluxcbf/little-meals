# Third-party icon attribution

## `ingredients/`

Icons in this directory come from several open-licensed icon families, all
retrieved unmodified via the [Iconify API](https://iconify.design/)
(`api.iconify.design`). See `ingredients/manifest.json`'s `source` field for
the exact icon behind each file (prefix before the `:` identifies the family
below).

| Prefix | Family | Author | License |
|---|---|---|---|
| `mdi` | [Material Design Icons](https://github.com/Templarian/MaterialDesign) | [Pictogrammers](https://pictogrammers.com/) | [Apache License 2.0](https://github.com/Templarian/MaterialDesign/blob/master/LICENSE) |
| `tdesign` | [TDesign Icons](https://github.com/Tencent/tdesign-icons) | Tencent | [MIT](https://github.com/Tencent/tdesign-icons/blob/main/LICENSE) |
| `tabler` | [Tabler Icons](https://github.com/tabler/tabler-icons) | Tabler | [MIT](https://github.com/tabler/tabler-icons/blob/master/LICENSE) |
| `icon-park-outline` | [IconPark](https://github.com/bytedance/IconPark) | ByteDance | [Apache License 2.0](https://github.com/bytedance/IconPark/blob/master/LICENSE) |
| `streamline` | [Streamline Icons](https://github.com/webalys-hq/streamline-icons-free) | Webalys | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) - attribution required, satisfied by this notice |
| `solar` | [Solar Icons](https://www.figma.com/community/file/1166831539721848736), as redistributed on [Iconify](https://icon-sets.iconify.design/solar/) | 480 Design | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) per Iconify's collection metadata - attribution required, satisfied by this notice. Distinct from `480-Design/Solar-Icon-Set` on GitHub (see below) - same icon designs, but this is Iconify's own redistribution under a confirmed license. |
| `lucide` | [Lucide](https://github.com/lucide-icons/lucide) | Lucide contributors | [ISC](https://github.com/lucide-icons/lucide/blob/main/LICENSE) |
| `boxicons` | [BoxIcons](https://github.com/box-icons/boxicons-core) | Box Icons | [MIT](https://github.com/box-icons/boxicons-core/blob/main/LICENSE) |
| `hugeicons` | [Hugeicons Free](https://hugeicons.com/) | Hugeicons | MIT |
| `material-symbols` | [Material Symbols](https://github.com/google/material-design-icons) | Google | [Apache License 2.0](https://github.com/google/material-design-icons/blob/master/LICENSE) |
| `game-icons` | [Game-icons.net](https://github.com/game-icons/icons) | Various (see project) | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) - attribution required, satisfied by this notice |

`ginger.svg` is a small hand-drawn original (not from any icon set) - no
open-licensed line icon for a ginger root exists in any family checked
(searched mdi, tdesign, tabler, icon-park-outline, solar, streamline, lucide,
boxicons, hugeicons, material-symbols, game-icons, and a broad unrestricted
Iconify search - only colorful emoji sets have one, wrong style for this
library).

Each SVG is single-color (`currentColor` fill and/or stroke), so it's tinted
via CSS `color` rather than needing separate white/transparent raster
variants.

Deliberately not vendored: `480-Design/Solar-Icon-Set` on GitHub, despite
being the milestone's original proposed source - its repo carries no LICENSE
file (GitHub reports `license: null`), so it isn't actually redistributable
under any confirmed terms. The `solar` prefix above is a different,
confirmed-license redistribution of the same icon designs via Iconify, not
this GitHub repo.
