import 'package:flutter_test/flutter_test.dart';
import 'package:venera_next/features/webdav_library/webdav_library.dart';
import 'package:venera_next/foundation/appdata.dart';

void main() {
  late _FakeWebDavLibraryOps ops;

  setUp(() {
    ops = _FakeWebDavLibraryOps();
    WebDavLibrarySource.ops = ops;
    appdata.settings['webdavComicLibrary'] = [
      'https://example.com/dav',
      'user',
      'pass',
    ];
    appdata.settings['webdavComicLibraryPath'] = '/manga/';
  });

  tearDown(() {
    WebDavLibrarySource.resetOps();
    appdata.settings['webdavComicLibrary'] = [];
    appdata.settings['webdavComicLibraryPath'] = '/venera_comics/';
  });

  test('loadComics lists directories and ignores archives', () async {
    ops.dirs['/manga/'] = const [
      WebDavLibraryEntry(name: 'Cat Eye', isDirectory: true),
      WebDavLibraryEntry(name: 'archive.cbz', isDirectory: false),
      WebDavLibraryEntry(name: '.DS_Store', isDirectory: false),
    ];

    final result = await WebDavLibrarySource.loadComics(1);

    expect(result.success, isTrue);
    expect(result.data.single.cover, '');
    expect(result.subData, 1);
    expect(result.data.map((comic) => comic.title), ['Cat Eye']);
    expect(result.data.single.sourceKey, WebDavLibrarySource.sourceKey);
  });

  test(
    'loadComicInfo detects chapter directories without scanning chapters',
    () async {
      ops.dirs['/manga/Cat Eye/'] = const [
        WebDavLibraryEntry(name: '第01卷', isDirectory: true),
        WebDavLibraryEntry(name: '第02卷', isDirectory: true),
        WebDavLibraryEntry(name: 'book.cbz', isDirectory: false),
      ];
      ops.dirs['/manga/Cat Eye/第01卷/'] = const [
        WebDavLibraryEntry(name: '002.jpg', isDirectory: false),
        WebDavLibraryEntry(name: '001.jpg', isDirectory: false),
      ];
      ops.dirs['/manga/Cat Eye/第02卷/'] = const [
        WebDavLibraryEntry(name: '001.webp', isDirectory: false),
      ];

      final result = await WebDavLibrarySource.loadComicInfo('Cat Eye');

      expect(result.success, isTrue);
      expect(result.data.cover, '');
      expect(result.data.chapters!.allChapters, {
        '第01卷': '第01卷',
        '第02卷': '第02卷',
      });
      expect(ops.readPaths, ['/manga/Cat Eye/']);
    },
  );

  test(
    'loadComicInfo handles Chinese comic and chapter directories from unmodifiable lists',
    () async {
      ops.dirs['/manga/猫之眼[北条司]/'] = List.unmodifiable([
        const WebDavLibraryEntry(name: '第01卷', isDirectory: true),
        const WebDavLibraryEntry(name: '第02卷', isDirectory: true),
      ]);
      ops.dirs['/manga/猫之眼[北条司]/第01卷/'] = List.unmodifiable([
        const WebDavLibraryEntry(name: '002.jpg', isDirectory: false),
        const WebDavLibraryEntry(name: '001.jpg', isDirectory: false),
      ]);
      ops.dirs['/manga/猫之眼[北条司]/第02卷/'] = List.unmodifiable([
        const WebDavLibraryEntry(name: '001.webp', isDirectory: false),
      ]);

      final result = await WebDavLibrarySource.loadComicInfo('猫之眼[北条司]');

      expect(result.success, isTrue);
      expect(result.data.cover, '');
      expect(result.data.chapters!.allChapters, {
        '第01卷': '第01卷',
        '第02卷': '第02卷',
      });
      expect(ops.readPaths, ['/manga/猫之眼[北条司]/']);
    },
  );

  test('loadComicInfo uses root cover and root images when present', () async {
    ops.dirs['/manga/Cat Eye/'] = const [
      WebDavLibraryEntry(name: 'cover.jpg', isDirectory: false),
      WebDavLibraryEntry(name: '002.jpg', isDirectory: false),
      WebDavLibraryEntry(name: '001.jpg', isDirectory: false),
    ];

    final result = await WebDavLibrarySource.loadComicInfo('Cat Eye');

    expect(result.success, isTrue);
    expect(result.data.cover, '/manga/Cat Eye/cover.jpg');
    expect(result.data.chapters, isNull);
  });

  test('loadComicPages returns chapter image paths in reading order', () async {
    ops.dirs['/manga/Cat Eye/第01卷/'] = const [
      WebDavLibraryEntry(name: 'cover.jpg', isDirectory: false),
      WebDavLibraryEntry(name: '010.jpg', isDirectory: false),
      WebDavLibraryEntry(name: '002.jpg', isDirectory: false),
    ];

    final result = await WebDavLibrarySource.loadComicPages('Cat Eye', '第01卷');

    expect(result.success, isTrue);
    expect(result.data, [
      '/manga/Cat Eye/第01卷/002.jpg',
      '/manga/Cat Eye/第01卷/010.jpg',
    ]);
  });

  test('loadComicPages handles Chinese directory paths', () async {
    ops.dirs['/manga/猫之眼[北条司]/第01卷/'] = List.unmodifiable([
      const WebDavLibraryEntry(name: '010.jpg', isDirectory: false),
      const WebDavLibraryEntry(name: '002.jpg', isDirectory: false),
    ]);

    final result = await WebDavLibrarySource.loadComicPages('猫之眼[北条司]', '第01卷');

    expect(result.success, isTrue);
    expect(result.data, [
      '/manga/猫之眼[北条司]/第01卷/002.jpg',
      '/manga/猫之眼[北条司]/第01卷/010.jpg',
    ]);
  });

  test(
    'getImageLoadingConfig builds encoded URL and basic auth header',
    () async {
      final config = await WebDavLibrarySource.getImageLoadingConfig(
        '/manga/Cat Eye/第01卷/001.jpg',
        'Cat Eye',
        '第01卷',
      );

      expect(
        config['url'],
        'https://example.com/dav/manga/Cat%20Eye/%E7%AC%AC01%E5%8D%B7/001.jpg',
      );
      expect(config['headers'], {'authorization': 'Basic dXNlcjpwYXNz'});
    },
  );
}

class _FakeWebDavLibraryOps implements WebDavLibraryOps {
  final dirs = <String, List<WebDavLibraryEntry>>{};
  final readPaths = <String>[];

  @override
  Future<List<WebDavLibraryEntry>> readDir(
    WebDavLibraryConfig config,
    String remotePath,
  ) async {
    readPaths.add(remotePath);
    return dirs[remotePath] ?? const [];
  }

  @override
  Future<void> test(WebDavLibraryConfig config) async {}
}
