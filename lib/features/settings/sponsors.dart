import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher_string.dart';
import 'package:venera_next/components/appbar.dart';
import 'package:venera_next/components/button.dart';
import 'package:venera_next/components/scroll.dart';
import 'package:venera_next/foundation/context.dart';
import 'package:venera_next/foundation/log.dart';
import 'package:venera_next/foundation/translations.dart';
import 'package:venera_next/foundation/widget_utils.dart';
import 'package:venera_next/network/app_dio.dart';

const _afdianUrl = "https://ifdian.net/a/cyril";

const _sources = [
  "https://cdn.jsdelivr.net/gh/CyrilPeng/venera-next@main/sponsors.json",
  "https://raw.githubusercontent.com/CyrilPeng/venera-next/main/sponsors.json",
];

class Sponsor {
  const Sponsor(this.name, this.tier);

  final String name;

  final int tier;
}

class _TierStyle {
  const _TierStyle(this.label, {required this.bold, required this.crown});

  final String label;

  final bool bold;

  final bool crown;
}

const _tierStyles = <int, _TierStyle>{
  200: _TierStyle("Tycoon Sponsor", bold: true, crown: true),
  80: _TierStyle("Hall of Fame", bold: true, crown: false),
  30: _TierStyle("Supporter", bold: false, crown: false),
};

class SponsorsPage extends StatefulWidget {
  const SponsorsPage({super.key});

  @override
  State<SponsorsPage> createState() => _SponsorsPageState();
}

class _SponsorsPageState extends State<SponsorsPage> {
  late Future<List<Sponsor>> _sponsors = _fetchSponsors();

  Future<List<Sponsor>> _fetchSponsors() async {
    Object? lastError;
    for (var url in _sources) {
      try {
        var res = await AppDio().get(
          url,
          options: Options(headers: {"cache-time": "long"}),
        );
        if (res.statusCode == 200) {
          var data = res.data is String ? jsonDecode(res.data) : res.data;
          var list = data["sponsors"];
          if (list is List) {
            return [
              for (var e in list)
                Sponsor(e["name"].toString(), (e["tier"] as num).toInt()),
            ];
          }
        }
      } catch (e, s) {
        lastError = e;
        Log.error("Sponsors", "Failed to fetch sponsors from $url", s);
      }
    }
    if (lastError != null) {
      throw lastError;
    }
    return const [];
  }

  void _retry() {
    setState(() {
      _sponsors = _fetchSponsors();
    });
  }

  @override
  Widget build(BuildContext context) {
    return SmoothCustomScrollView(
      slivers: [
        SliverAppbar(title: Text("Sponsors".tl)),
        FutureBuilder<List<Sponsor>>(
          future: _sponsors,
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const SliverFillRemaining(
                hasScrollBody: false,
                child: Center(child: CircularProgressIndicator()),
              );
            }
            if (snapshot.hasError) {
              return SliverFillRemaining(
                hasScrollBody: false,
                child: Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text("Failed to load sponsors".tl),
                      const SizedBox(height: 12),
                      Button.text(
                        onPressed: _retry,
                        child: Text("Retry".tl),
                      ),
                    ],
                  ),
                ),
              );
            }
            return SliverToBoxAdapter(
              child: _buildContent(snapshot.data ?? const []),
            );
          },
        ),
      ],
    );
  }

  Widget _buildContent(List<Sponsor> sponsors) {
    var children = <Widget>[
      Text(
        "Thanks to all sponsors who support the continuous maintenance of VeneraNext."
            .tl,
        style: const TextStyle(fontSize: 14),
      ).paddingHorizontal(16).paddingTop(8),
    ];

    if (sponsors.isEmpty) {
      children.add(
        Center(
          child: Text("No sponsors yet".tl).paddingAll(32),
        ),
      );
    } else {
      var groups = <int, List<Sponsor>>{};
      for (var sponsor in sponsors) {
        groups.putIfAbsent(sponsor.tier, () => []).add(sponsor);
      }
      var tiers = groups.keys.toList()..sort((a, b) => b.compareTo(a));
      for (var tier in tiers) {
        var style =
            _tierStyles[tier] ??
            const _TierStyle("", bold: false, crown: false);
        children.add(_buildTierHeader(tier, style));
        children.add(_buildSponsorChips(groups[tier]!, style));
      }
    }

    children.add(
      Center(
        child: Button.filled(
          onPressed: () => launchUrlString(_afdianUrl),
          child: Text("Support on Afdian".tl),
        ).paddingVertical(24),
      ),
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: children,
    ).paddingBottom(16);
  }

  Widget _buildTierHeader(int tier, _TierStyle style) {
    var prefix = style.crown ? "👑 " : "";
    var label = style.label.isEmpty ? "" : "${style.label.tl} ";
    return Text(
      "$prefix$label（¥$tier/月）",
      style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
    ).paddingHorizontal(16).paddingTop(20).paddingBottom(8);
  }

  Widget _buildSponsorChips(List<Sponsor> sponsors, _TierStyle style) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [for (var sponsor in sponsors) _buildChip(sponsor, style)],
    ).paddingHorizontal(16);
  }

  Widget _buildChip(Sponsor sponsor, _TierStyle style) {
    var colorScheme = context.colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: style.crown
            ? colorScheme.primaryContainer
            : colorScheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (style.crown) ...[
            const Text("👑"),
            const SizedBox(width: 4),
          ],
          Text(
            sponsor.name,
            style: TextStyle(
              fontWeight: style.bold ? FontWeight.w700 : FontWeight.normal,
              color: style.crown ? colorScheme.onPrimaryContainer : null,
            ),
          ),
        ],
      ),
    );
  }
}
