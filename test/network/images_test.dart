import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:venera/network/images.dart';

void main() {
  tearDown(() {
    ImageDownloader.debugLoadComicImageUnwrapped = null;
    ImageDownloader.cancelAllLoadingImages();
  });

  test(
    'loadComicImage cancels source stream after last listener cancels',
    () async {
      final sourceCanceled = Completer<void>();
      final source = StreamController<ImageDownloadProgress>(
        onCancel: () {
          if (!sourceCanceled.isCompleted) {
            sourceCanceled.complete();
          }
        },
      );
      addTearDown(() async {
        if (!source.isClosed) {
          await source.close();
        }
      });

      ImageDownloader.debugLoadComicImageUnwrapped =
          (imageKey, sourceKey, cid, eid) => source.stream;

      final subscription = ImageDownloader.loadComicImage(
        'image-1',
        'source',
        'comic',
        'chapter',
      ).listen((_) {});
      await pumpEventQueue();

      await subscription.cancel();

      await sourceCanceled.future.timeout(const Duration(seconds: 1));
    },
  );

  test('cancelAllLoadingImages cancels active source streams', () async {
    final sourceCanceled = Completer<void>();
    final source = StreamController<ImageDownloadProgress>(
      onCancel: () {
        if (!sourceCanceled.isCompleted) {
          sourceCanceled.complete();
        }
      },
    );
    addTearDown(() async {
      if (!source.isClosed) {
        await source.close();
      }
    });

    ImageDownloader.debugLoadComicImageUnwrapped =
        (imageKey, sourceKey, cid, eid) => source.stream;

    final subscription = ImageDownloader.loadComicImage(
      'image-2',
      'source',
      'comic',
      'chapter',
    ).listen((_) {});
    await pumpEventQueue();

    ImageDownloader.cancelAllLoadingImages();

    await sourceCanceled.future.timeout(const Duration(seconds: 1));
    await subscription.cancel();
  });
}
