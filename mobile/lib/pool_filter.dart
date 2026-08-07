/// 문항 묶음을 거르는 잣대 하나와, 그것을 고르는 칩 줄.
///
/// 「안 푼 것 먼저」 세 줄이 홈·직렬·과목에 똑같이 복붙돼 있었다. 여기로 모은다.
library;

import 'package:flutter/material.dart';
import 'models.dart';
import 'store.dart';
import 'theme.dart';
import 'widgets.dart';

enum PoolFilter {
  all('전체'),
  untried('안 푼 것'),
  wrong('틀린 것'),
  marked('북마크');

  const PoolFilter(this.label);
  final String label;

  bool test(String id) {
    final s = Store.instance;
    return switch (this) {
      PoolFilter.all => true,
      PoolFilter.untried => !s.tried(id),
      PoolFilter.wrong => s.isWrong(id),
      PoolFilter.marked => s.isMarked(id),
    };
  }

  List<Item> apply(List<Item> items) =>
      this == PoolFilter.all ? items : items.where((i) => test(i.id)).toList();

  /// 걸러 낸 것이 없으면 원본을 돌려준다.
  ///
  /// 「안 푼 것」으로 풀다가 다 풀고 나면 묶음이 비는데, 그때 빈 화면을 내미느니
  /// 전체를 다시 내는 편이 낫다. 웹판이 하던 것과 같다.
  List<Item> applyOrAll(List<Item> items) {
    final out = apply(items);
    return out.isEmpty ? items : out;
  }
}

/// 화면 위쪽 칩 줄. 각 칩에 지금 걸리는 문항 수를 함께 보인다 —
/// 눌러 보기 전에 몇 개인지 알아야 고를 값이 있다.
class PoolFilterBar extends StatelessWidget {
  final List<Item> items;
  final PoolFilter value;
  final ValueChanged<PoolFilter> onChanged;
  const PoolFilterBar({
    super.key, required this.items, required this.value, required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: [
          for (final f in PoolFilter.values)
            ChipButton(
              label: f.label,
              count: f == PoolFilter.all ? items.length : f.apply(items).length,
              on: f == value,
              onTap: () => onChanged(f),
            ),
        ],
      ),
    );
  }
}

/// 필터가 걸려 아무것도 안 남았을 때 그 사실을 말해 준다.
class FilterEmpty extends StatelessWidget {
  final PoolFilter filter;
  const FilterEmpty(this.filter, {super.key});
  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    final why = switch (filter) {
      PoolFilter.untried => '이 안의 문항을 모두 풀었습니다.',
      PoolFilter.wrong => '틀린 채로 남아 있는 문항이 없습니다.',
      PoolFilter.marked => '여기에는 북마크한 문항이 없습니다.',
      PoolFilter.all => '문항이 없습니다.',
    };
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 28),
      child: Center(
        child: Text('「${filter.label}」에 해당하는 문항이 없습니다.\n$why',
            textAlign: TextAlign.center,
            style: TextStyle(color: c.faint, fontSize: 13.5, height: 1.5)),
      ),
    );
  }
}
