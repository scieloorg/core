var scieloLib = {
	IsMobile: false,
	IsTablet: false,
	IsTabletPortrait: false,
	IsDesktop: false,
	IsHD: false,
	isOldIE: false,
	DetectMobile: function (userAgent) {
		var mobile = {};

		// valores do http://detectmobilebrowsers.com/
		mobile.detectMobileBrowsers = {
			fullPattern: /(android|bb\d+|meego).+mobile|avantgo|bada\/|blackberry|blazer|compal|elaine|fennec|hiptop|iemobile|ip(hone|od)|iris|kindle|lge |maemo|midp|mmp|mobile.+firefox|netfront|opera m(ob|in)i|palm( os)?|phone|p(ixi|re)\/|plucker|pocket|psp|series(4|6)0|symbian|treo|up\.(browser|link)|vodafone|wap|windows ce|xda|xiino/i,
			shortPattern: /1207|6310|6590|3gso|4thp|50[1-6]i|770s|802s|a wa|abac|ac(er|oo|s\-)|ai(ko|rn)|al(av|ca|co)|amoi|an(ex|ny|yw)|aptu|ar(ch|go)|as(te|us)|attw|au(di|\-m|r |s )|avan|be(ck|ll|nq)|bi(lb|rd)|bl(ac|az)|br(e|v)w|bumb|bw\-(n|u)|c55\/|capi|ccwa|cdm\-|cell|chtm|cldc|cmd\-|co(mp|nd)|craw|da(it|ll|ng)|dbte|dc\-s|devi|dica|dmob|do(c|p)o|ds(12|\-d)|el(49|ai)|em(l2|ul)|er(ic|k0)|esl8|ez([4-7]0|os|wa|ze)|fetc|fly(\-|_)|g1 u|g560|gene|gf\-5|g\-mo|go(\.w|od)|gr(ad|un)|haie|hcit|hd\-(m|p|t)|hei\-|hi(pt|ta)|hp( i|ip)|hs\-c|ht(c(\-| |_|a|g|p|s|t)|tp)|hu(aw|tc)|i\-(20|go|ma)|i230|iac( |\-|\/)|ibro|idea|ig01|ikom|im1k|inno|ipaq|iris|ja(t|v)a|jbro|jemu|jigs|kddi|keji|kgt( |\/)|klon|kpt |kwc\-|kyo(c|k)|le(no|xi)|lg( g|\/(k|l|u)|50|54|\-[a-w])|libw|lynx|m1\-w|m3ga|m50\/|ma(te|ui|xo)|mc(01|21|ca)|m\-cr|me(rc|ri)|mi(o8|oa|ts)|mmef|mo(01|02|bi|de|do|t(\-| |o|v)|zz)|mt(50|p1|v )|mwbp|mywa|n10[0-2]|n20[2-3]|n30(0|2)|n50(0|2|5)|n7(0(0|1)|10)|ne((c|m)\-|on|tf|wf|wg|wt)|nok(6|i)|nzph|o2im|op(ti|wv)|oran|owg1|p800|pan(a|d|t)|pdxg|pg(13|\-([1-8]|c))|phil|pire|pl(ay|uc)|pn\-2|po(ck|rt|se)|prox|psio|pt\-g|qa\-a|qc(07|12|21|32|60|\-[2-7]|i\-)|qtek|r380|r600|raks|rim9|ro(ve|zo)|s55\/|sa(ge|ma|mm|ms|ny|va)|sc(01|h\-|oo|p\-)|sdk\/|se(c(\-|0|1)|47|mc|nd|ri)|sgh\-|shar|sie(\-|m)|sk\-0|sl(45|id)|sm(al|ar|b3|it|t5)|so(ft|ny)|sp(01|h\-|v\-|v )|sy(01|mb)|t2(18|50)|t6(00|10|18)|ta(gt|lk)|tcl\-|tdg\-|tel(i|m)|tim\-|t\-mo|to(pl|sh)|ts(70|m\-|m3|m5)|tx\-9|up(\.b|g1|si)|utst|v400|v750|veri|vi(rg|te)|vk(40|5[0-3]|\-v)|vm40|voda|vulc|vx(52|53|60|61|70|80|81|83|85|98)|w3c(\-| )|webc|whit|wi(g |nc|nw)|wmlb|wonu|x700|yas\-|your|zeto|zte\-/i
		};

		return mobile.detectMobileBrowsers.fullPattern.test(userAgent) ||
			mobile.detectMobileBrowsers.shortPattern.test(userAgent.substr(0, 4));
	},
	DetectTablet: function (userAgent) {
		var tablets = {};

		// valores do http://detectmobilebrowsers.com/
		tablets.detectMobileBrowsers = {
			tabletPattern: /android|ipad|playbook|silk/i
		};

		return tablets.detectMobileBrowsers.tabletPattern.test(userAgent);
	},
	SetScreen: function () {
		var w = $(window).innerWidth();

		if (w > 990) scieloLib.IsDesktop = true;
		if (w > 1206) scieloLib.IsHD = true;

		if (scieloLib.DetectMobile(navigator.userAgent))
			scieloLib.IsMobile = true;

		if (scieloLib.DetectTablet(navigator.userAgent)) {
			scieloLib.IsTablet = true;

			var orientation = window.matchMedia("(orientation: portrait)").matches;

			if (orientation)
				scieloLib.IsTabletPortrait = true;
			else
				scieloLib.IsTabletPortrait = false;

			window.addEventListener("orientationchange", function () {
				if (screen.orientation.angle == 0)
					scieloLib.IsTabletPortrait = true;
				else
					scieloLib.IsTabletPortrait = false;
			});
		}

		if (navigator.appVersion.indexOf("MSIE 8") > -1) {
			scieloLib.IsMobile = false;
			scieloLib.IsTablet = false;
			scieloLib.IsDesktop = true;
			scieloLib.IsOldIE = true;
			scieloLib.IsHD = false;
			$("html").addClass("lt-ie9");
		}
	},
	SetMatching: function(label, matching) {

		$('#matchingButton').html(label + ' <span class="caret"></span>');
		$('#matching').val(matching);
	},
	InitializeSlickTo: function (selector) {
		selector.slick({
			dots: false,
			infinite: true,
			slidesToShow: 3,
			slidesToScroll: 3,
			responsive: [{
				breakpoint: 640,
				settings: {
					slidesToShow: 1,
					slidesToScroll: 1
				}
			}]
		});
	},
	IsSlickInitializedTo: function (selector) {
		return selector.hasClass('slick-initialized');
	},
	UnInitializeSlickTo: function (selector) {
		selector.slick('unslick');
	},
	Init: function () {

		scieloLib.SetScreen();

		//abre menu share
		$("#dropdown-menu-share").click(function (e) {

			var t = $(this);

			e.preventDefault();
			$('.menu-share').show();
		});

		//fecha menu share
		$(document).on('click', function (e) {
			if (!$(e.target).closest('.dropdown-toggle').length) $('.menu-share').hide();
		});

		// Fecha o alert notification ao clicar no X
		$(".close").click(function () {
			$(".alert-notification").slideUp("fast");
		});

		// Variables and selectors
		var ACTIVE_CSS = 'active';
		var BTN_TAB_MOBILE = $(".btn-tab-mobile");
		var TAB_PANE = $(".tab-pane");
		var TAB_BLOG = $("#tab-blog");
		var SLIDER_BLOG = $(".slider-blog");
		var SLIDER_TWITTER = $(".slider-twitter");
		var SLIDER_YOUTUBE_VIDEOS = $(".slider-youtube-videos");
		var ROW_TAB_MOBILE = $(".row-tab-mobile");
		var ROW_TAB_DESK = $(".row-tab-desk");

		var BTN_ACCORDION = $(".btn-accordion");
		var ROW_ACCORDION = $(".row-accordion");

		// Local function to be used in mobile
		var REMOVE_ACTIVE_CLASS_MOBILE = function () {
			BTN_TAB_MOBILE.removeClass(ACTIVE_CSS);
			TAB_PANE.removeClass(ACTIVE_CSS);
		};


		// Todas as tabs ficam inativas e todas as tab-pane ficam fechadas
		if (scieloLib.IsMobile) {

			REMOVE_ACTIVE_CLASS_MOBILE();

			ROW_TAB_MOBILE.show();
			ROW_TAB_DESK.hide();

			// Tab-blog recebe classe active e inicializa o slider blog
		} else if (scieloLib.IsDesktop || scieloLib.IsTablet) {

			TAB_BLOG.addClass(ACTIVE_CSS);
			scieloLib.InitializeSlickTo(SLIDER_BLOG);

			ROW_TAB_MOBILE.hide();
			ROW_TAB_DESK.show();

			if (scieloLib.IsDesktop) {
				$(".showTooltip").tooltip();
			}
		}

		// 'btn-tab-mobile' deve ter comportamento de accordion: Quando ta fechado, clicou, abre. Quando ta aberto, clicou fecha.
		BTN_TAB_MOBILE.click(function (e) {
			e.preventDefault();

			var btnTabMobile = $(this);
			var tabPane = $(btnTabMobile.attr('href'));

			if (btnTabMobile.hasClass(ACTIVE_CSS)) {

				btnTabMobile.removeClass(ACTIVE_CSS);

				setTimeout(function () {
					tabPane.removeClass(ACTIVE_CSS);
				}, 100);

			} else {

				REMOVE_ACTIVE_CLASS_MOBILE();

				btnTabMobile.slideDown().addClass(ACTIVE_CSS);
			}
		});

		//accordion
		BTN_ACCORDION.click(function (e) {
			e.preventDefault();

			var btnAccordion = $(this);
			var tabPane = $(btnAccordion.attr('href'));

			if (btnAccordion.hasClass(ACTIVE_CSS)) {

				btnAccordion.removeClass(ACTIVE_CSS);

				setTimeout(function () {
					tabPane.slideUp();
				}, 100);

			} else {

				$(".row-accordion-content").removeClass('active');
				tabPane.slideDown();
				btnAccordion.addClass(ACTIVE_CSS);
			}
		});

		// Ao mostrar uma tab
		$('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {

			var tabID = $(e.target).attr('href');
			var isTabTwitter = (tabID == '#tab-twitter');
			var isTabBlog = (tabID == '#tab-blog');
			var isTabBlog = (tabID == '#tab-blog');
			var isTabYoutubeVideos = (tabID == '#tab-youtube-videos');

			// Se for a tab do twitter, ativa o slider do twitter
			if (isTabTwitter) {

				if (scieloLib.IsSlickInitializedTo(SLIDER_TWITTER)) {
					scieloLib.UnInitializeSlickTo(SLIDER_TWITTER);
				}

				scieloLib.InitializeSlickTo(SLIDER_TWITTER);
			}

			// Se for a tab do blog, ativa o slider do blog
			if (isTabBlog) {

				if (scieloLib.IsSlickInitializedTo(SLIDER_BLOG)) {
					scieloLib.UnInitializeSlickTo(SLIDER_BLOG);
				}

				scieloLib.InitializeSlickTo(SLIDER_BLOG);
			}

			// Se for a tab do youtube, ativa o slider do youtube
			if (isTabYoutubeVideos) {

				if (scieloLib.IsSlickInitializedTo(SLIDER_YOUTUBE_VIDEOS)) {
					scieloLib.UnInitializeSlickTo(SLIDER_YOUTUBE_VIDEOS);
				}

				scieloLib.InitializeSlickTo(SLIDER_YOUTUBE_VIDEOS);
			}
		});


		// Toggle discontinued collection
		
		$(".discontinued-toggle").click(function(e) {
			e.preventDefault();
			$(".discontinued-item").toggle( "slow");
			$(this).toggleClass("discontinued-toggle-off discontinued-toggle-on");
		});
		
	}
};
